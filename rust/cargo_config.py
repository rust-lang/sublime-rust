"""Sublime commands for configuring Cargo execution.

See `cargo_settings` for more details on how settings work.
"""

import os
import re
import sublime_plugin
from .cargo_settings import CargoSettings, CARGO_COMMANDS, LoadSettingsError
from .util import index_with
from . import rust_proc

# Keep track of recent choices to set the default value.
RECENT_CHOICES = {}


class CargoConfigBase(sublime_plugin.WindowCommand):

    """Base class for cargo config commands.

    This implements a simple interactive UI by asking the user a series of
    questions using the Sublime quick panels for selecting choices. Subclasses
    set the `sequence` class variable to the list of questions they want to
    ask.  The choices for each question are produced by methods starting with
    'items_'+name.  These methods should return a dictionary with:

    - `items`: List of choices.  Each element should be a tuple
      `(display_string, value)`.
    - `default`: The default value (optional).
    - `skip_if_one`: Skip this question if there is only 1 item.

    `items_` methods can also just return the 'items' list.

    An optional method `selected_`+name will be called when a choice is made.
    This method can return a list of questions to be asked.

    The `done` method is called once all questions have been asked.

    Callers are allowed to pass in values instead of using the interactive UI.
    This is probably only useful for the test code, but in theory you could
    define key bindings that perform certain actions.
    """

    # CargoSettings object.
    settings = None
    # Dictionary of choices passed into the command, instead of using
    # interactive UI.
    input = None

    # Sequence of questions to ask.
    sequence = None
    # Current question being asked.
    sequence_index = 0
    # Dictionary of selections made during the interactive process.
    choices = None

    def run(self, **kwargs):
        self.sequence_index = 0
        # Copy, since WindowCommand reuses objects.
        self._sequence = self.sequence[:]
        self.input = kwargs
        self.settings = CargoSettings(self.window)
        try:
            self.settings.load()
        except LoadSettingsError:
            return
        self.choices = {}
        self.show_next_question()

    def done(self):
        """Called once all questions have been asked.  Subclasses must
        implement this."""
        raise NotImplementedError()

    def show_next_question(self):
        if self.sequence_index < len(self._sequence):
            q = self._sequence[self.sequence_index]
            self.sequence_index += 1
        else:
            self.done()
            return

        item_info = getattr(self, 'items_' + q)()
        if not isinstance(item_info, dict):
            item_info = {'items': item_info}

        f_selected = getattr(self, 'selected_' + q, None)

        def make_choice(value):
            self.choices[q] = value
            if f_selected:
                next = f_selected(value)
                if next:
                    self._sequence.extend(next)
            self.show_next_question()

        if q in self.input:
            make_choice(self.input[q])
        else:
            if 'items' in item_info:
                def wrapper(index):
                    if index != -1:
                        chosen = item_info['items'][index][1]
                        RECENT_CHOICES[q] = chosen
                        make_choice(chosen)

                items = item_info['items']
                if item_info.get('skip_if_one', False) and len(items) == 1:
                    wrapper(0)
                else:
                    # If the user manually edits the config and enters custom
                    # values then it won't show up in the list (because it is
                    # not an exact match).  Add it so that it is a valid
                    # choice (assuming the user entered a valid value).
                    if 'default' in item_info:
                        default_index = index_with(items,
                            lambda x: x[1] == item_info['default'])
                        if default_index == -1:
                            items.append((item_info['default'],
                                          item_info['default']))
                    # Determine the default selection.
                    # Use the default provided by the items_ method, else
                    # use the most recently used value.
                    default = index_with(items,
                        lambda x: x[1] == item_info.get('default',
                            RECENT_CHOICES.get(q, '_NO_DEFAULT_SENTINEL_')))
                    display_items = [x[0] for x in items]
                    self.window.show_quick_panel(display_items, wrapper, 0,
                                                 default)
            elif 'caption' in item_info:
                self.window.show_input_panel(item_info['caption'],
                                             item_info.get('default', ''),
                                             make_choice, None, None)
            else:
                raise ValueError(item_info)

    def items_package(self):
        # path/to/package: package_info
        self.packages = {}

        def _add_manifest(path):
            manifest = self.settings.get_cargo_metadata(path)
            if manifest:
                for package in manifest['packages']:
                    manifest_dir = os.path.dirname(package['manifest_path'])
                    if manifest_dir not in self.packages:
                        self.packages[manifest_dir] = package
            else:
                # Manifest load failure, let it slide.
                print('Failed to load Cargo manifest in %r' % path)

        _add_manifest(self.settings.manifest_dir)
        skeys = self.settings.project_data.get('settings', {})\
                                          .get('cargo_build', {})\
                                          .get('paths', {}).keys()
        for path in skeys:
            if path not in self.packages:
                _add_manifest(path)

        items = [('Package:' + package['name'], path)
            for path, package in self.packages.items()]
        items.sort(key=lambda x: x[0])
        return {
            'items': items,
            'skip_if_one': True
        }

    def items_target(self):
        # Group by kind.
        kinds = {}
        package_path = self.choices['package']
        for target in self.packages[package_path]['targets']:
            # AFAIK, when there are multiple "kind" values, this only happens
            # when there are multiple library kinds.
            kind = target['kind'][0]
            if kind in ('lib', 'rlib', 'dylib', 'staticlib', 'proc-macro'):
                kinds.setdefault('lib', []).append(('Lib', '--lib'))
            elif kind in ('bin', 'test', 'example', 'bench'):
                text = '%s: %s' % (kind.capitalize(), target['name'])
                arg = '--%s %s' % (kind, target['name'])
                kinds.setdefault(kind, []).append((text, arg))
            elif kind in ('custom-build',):
                # build.rs, can't be built explicitly.
                pass
            else:
                print('Rust: Unsupported target found: %s' % kind)
        items = [('All Targets', None),
                 ('Automatic Detection', 'auto')]
        for kind, values in kinds.items():
            allowed = True
            if self.choices.get('variant', None):
                cmd = CARGO_COMMANDS[self.choices['variant']]
                target_types = cmd['allows_target']
                if target_types is not True:
                    allowed = kind in target_types
            if allowed:
                items.extend(values)
        return items

    def items_variant(self):
        result = []
        for key, info in CARGO_COMMANDS.items():
            if self.filter_variant(info):
                result.append((info['name'], key))
        return result

    def filter_variant(self, x):
        return True


class CargoSetProfile(CargoConfigBase):

    sequence = ['package', 'target', 'profile']

    def items_profile(self):
        default = self.settings.get_with_target(self.choices['package'],
                                                self.choices['target'],
                                                'release', False)
        if default:
            default = 'release'
        else:
            default = 'dev'
        items = [('Dev', 'dev'),
                 ('Release', 'release')]
        return {'items': items,
                'default': default}

    def done(self):
        self.settings.set_with_target(self.choices['package'],
                                      self.choices['target'],
                                      'release',
                                      self.choices['profile'] == 'release')


class CargoSetTarget(CargoConfigBase):

    sequence = ['variant', 'package', 'target']

    def filter_variant(self, info):
        return info.get('allows_target', False)

    def items_target(self):
        items = super(CargoSetTarget, self).items_target()
        default = self.settings.get_with_variant(self.choices['package'],
                                                 self.choices['variant'],
                                                 'target')
        return {
            'items': items,
            'default': default
        }

    def done(self):
        self.settings.set_with_variant(self.choices['package'],
                                       self.choices['variant'],
                                       'target',
                                       self.choices['target'])


class CargoSetTriple(CargoConfigBase):

    sequence = ['package', 'target', 'target_triple']

    def items_target_triple(self):
        # Could check if rustup is not installed, to run
        # "rustc --print target-list", but that does not tell
        # us which targets are installed.
        triples = rust_proc.check_output(self.window,
            'rustup target list'.split(), self.settings.manifest_dir)\
            .splitlines()
        current = self.settings.get_with_target(self.choices['package'],
                                                self.choices['target'],
                                                'target_triple')
        result = [('Use Default', None)]
        for triple in triples:
            if triple.endswith(' (default)'):
                actual_triple = triple[:-10]
                result.append((actual_triple, actual_triple))
            elif triple.endswith(' (installed)'):
                actual_triple = triple[:-12]
                result.append((actual_triple, actual_triple))
            else:
                actual_triple = None
            # Don't bother listing uninstalled targets.
        return {
            'items': result,
            'default': current
        }

    def done(self):
        self.settings.set_with_target(self.choices['package'],
                                      self.choices['target'],
                                      'target_triple',
                                      self.choices['target_triple'])


class CargoSetToolchain(CargoConfigBase):

    sequence = ['which']

    def items_which(self):
        return [
            ('Set Toolchain for Build Variant', 'variant'),
            ('Set Toolchain for Targets', 'target')
        ]

    def selected_which(self, which):
        if which == 'variant':
            return ['package', 'variant', 'toolchain']
        elif which == 'target':
            return ['package', 'target', 'toolchain']
        else:
            raise AssertionError(which)

    def items_toolchain(self):
        items = [('Use Default Toolchain', None)]
        toolchains = self._toolchain_list()
        if self.choices['which'] == 'variant':
            current = self.settings.get_with_variant(self.choices['package'],
                                                     self.choices['variant'],
                                                     'toolchain')
        elif self.choices['which'] == 'target':
            current = self.settings.get_with_target(self.choices['package'],
                                                    self.choices['target'],
                                                    'toolchain')
        else:
            raise AssertionError(self.choices['which'])
        items.extend([(x, x) for x in toolchains])
        return {
            'items': items,
            'default': current
        }

    def _toolchain_list(self):
        output = rust_proc.check_output(self.window,
                                        'rustup toolchain list'.split(),
                                        self.settings.manifest_dir)
        output = output.splitlines()
        system_default = index_with(output, lambda x: x.endswith(' (default)'))
        if system_default != -1:
            output[system_default] = output[system_default][:-10]
        # Rustup supports some shorthand of either `channel` or `channel-date`
        # without the trailing target info.
        #
        # Complete list of available toolchains is available at:
        # https://static.rust-lang.org/dist/index.html
        # (See https://github.com/rust-lang-nursery/rustup.rs/issues/215)
        shorthands = []
        channels = ['nightly', 'beta', 'stable', '\d\.\d{1,2}\.\d']
        pattern = '(%s)(?:-(\d{4}-\d{2}-\d{2}))?(?:-(.*))' % '|'.join(channels)
        for toolchain in output:
            m = re.match(pattern, toolchain)
            # Should always match.
            if m:
                channel = m.group(1)
                date = m.group(2)
                if date:
                    shorthand = '%s-%s' % (channel, date)
                else:
                    shorthand = channel
                if shorthand not in shorthands:
                    shorthands.append(shorthand)
        result = shorthands + output
        result.sort()
        return result

    def done(self):
        if self.choices['which'] == 'variant':
            self.settings.set_with_variant(self.choices['package'],
                                           self.choices['variant'],
                                           'toolchain',
                                           self.choices['toolchain'])
        elif self.choices['which'] == 'target':
            self.settings.set_with_target(self.choices['package'],
                                          self.choices['target'],
                                          'toolchain',
                                          self.choices['toolchain'])
        else:
            raise AssertionError(self.choices['which'])


class CargoSetFeatures(CargoConfigBase):

    sequence = ['package', 'target', 'no_default_features', 'features']

    def items_no_default_features(self):
        current = self.settings.get_with_target(self.choices['package'],
                                                self.choices['target'],
                                                'no_default_features', False)
        items = [
            ('Include default features.', False),
            ('Do not include default features.', True)
        ]
        return {
            'items': items,
            'default': current,
        }

    def items_features(self):
        features = self.settings.get_with_target(self.choices['package'],
                                                 self.choices['target'],
                                                 'features', None)
        if features is None:
            package_path = self.choices['package']
            available_features = self.packages[package_path].get('features', {})
            items = list(available_features.keys())
            # Remove the "default" entry.
            if 'default' in items:
                del items[items.index('default')]
                if not self.choices['no_default_features']:
                    # Don't show default features, (they are already included).
                    for ft in available_features['default']:
                        if ft in items:
                            del items[items.index(ft)]
            features = ' '.join(items)
        return {
            'caption': 'Choose features (space separated, use "ALL" to use all features)',
            'default': features,
        }

    def done(self):
        self.settings.set_with_target(self.choices['package'],
                                      self.choices['target'],
                                      'no_default_features',
                                      self.choices['no_default_features'])
        self.settings.set_with_target(self.choices['package'],
                                      self.choices['target'],
                                      'features',
                                      self.choices['features'])
