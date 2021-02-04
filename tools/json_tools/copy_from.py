#!/usr/bin/env python3
'''
Fill in missing data from parents by `copy-from` field inheritance
'''

import re
import sys

from operator import add, mul  # for parametrizing

import inheritson

from util import import_data

LOADER_TYPE_FIELD = 'type'  # readability
INHERITANCE_FIELD = 'copy-from'

UNIQ_ID_FIELD = 'inheritson_id'
PARENT_UNIQ_ID_FIELD = 'inheritson_parent'

UNIT_SPLIT_RE = re.compile(
    r'(?P<number>[\d\+\-]+)'
    r'\s*'
    r'(?P<units>\w+)?')


def warn(message):
    '''
    Print the message to stderr
    '''
    print(message, file=sys.stderr)


class DefaultLoader:
    '''
    Base loader class
    '''
    id_field = 'id'
    assert_id = True

    def load(self, obj):
        '''
        Prepare the object for ... FIXME:
        '''
        obj = self.fix_id(obj)
        results = self.explode_id_lists(obj)
        results = map(self.prepare, results)
        return results

    def fix_id(self, obj):
        '''
        For the AbstractLoader to override and treat abstract value as id
        '''
        return obj

    def explode_id_lists(self, obj):
        '''
        Create duplicate objects for all id values in arrays
        '''
        # FIXME: fill looks_like with copy-from
        assert self.id_field in obj
        id_ = obj.get(self.id_field)
        if self.assert_id:
            assert id_

        if isinstance(id_, str):
            results = [obj]
        elif isinstance(id_, type(None)) and not self.assert_id:
            results = [obj]
        elif isinstance(id_, list):
            results = []
            for sub_id in id_:
                result = obj.copy()
                result[self.id_field] = sub_id
                results.append(result)
        else:
            id_data_type = type(id_)
            raise ValueError(
                f'Unknown {self.id_field} data type: {id_data_type}')

        return results

    def prepare(self, obj):
        '''
        Use tuple of type and id values as unique keys as id is not unique
        '''
        id_ = obj[self.id_field]
        type_ = obj[LOADER_TYPE_FIELD]
        obj[UNIQ_ID_FIELD] = (type_, id_)

        if INHERITANCE_FIELD in obj:
            obj[PARENT_UNIQ_ID_FIELD] = \
                (obj[LOADER_TYPE_FIELD], obj[INHERITANCE_FIELD])

        return obj

    def inherit(self, parent, child):
        '''
        Inheritance resolver, expected by inheritson
        '''
        assert parent, child
        result = parent.copy()

        # relative
        relative = child.get('relative', {})
        if relative:
            child = self.relative_changes(
                parent, child, relative, add)

        # proportional
        relative = child.get('proportional', {})
        if relative:
            child = self.relative_changes(
                parent, child, relative, mul)

        # FIXME: extend

        # FIXME: delete

        # FIXME: looks_like

        result.update(child)
        return result

    def split_units(self, value, target_type=float):
        '''
        Separate units from the value
        '''
        if isinstance(value, str):
            matched = UNIT_SPLIT_RE.match(value)
            number = target_type(matched.group("number"))
            units = matched.group("units")
        else:
            try:
                number = target_type(value)
            except TypeError:
                warn(f'Wrong type: {value}')
                raise
            units = ''

        return (number, units)

    def relative_changes(
            self, parent, child, changes, operation, skip=('vitamins',)):
        '''
        Resolve relative changes inheritance
        FIXME: empty skip
        '''
        for field_name, modifier in changes.items():
            if field_name in skip:
                continue
            parent_value = parent.get(field_name)
            print(parent_value, modifier, child)

            parent_suffix = ''
            modifier_suffix = ''
            if parent_value:
                parent_value, parent_suffix = self.split_units(parent_value)
            if modifier:
                modifier, modifier_suffix = self.split_units(modifier)
            if modifier_suffix and parent_suffix:
                assert modifier_suffix == parent_suffix

            if parent_value is None:
                warn(f'Empty parent value, setting to 0, {child}')
                parent_value = 0

            child[field_name] = operation(parent_value, modifier)

            if parent_suffix:
                child[field_name] = str(child[field_name]) + parent_suffix

        return child


class AbstractLoader(DefaultLoader):
    '''
    Uses abstract value as id
    '''
    abstract_field = 'abstract'

    def fix_id(self, obj):
        '''
        Treat abstract value as id
        '''
        id_ = obj.get(self.id_field)
        abstract = obj.get(self.abstract_field)
        if self.assert_id:
            assert bool(id_) ^ bool(abstract)  # one and only one is filled
        obj[self.id_field] = id_ or abstract
        return obj


class EmptyIDLoader(AbstractLoader):
    '''
    Do not expect id to be present
    '''
    assert_id = False


class RecipeLoader(AbstractLoader):
    '''
    Uses result field as id
    '''
    id_field = 'result'  # TODO: compound results?

    '''
            if( relative.has_int( "vitamins" ) ) {
            // allows easy specification of 'fortified' comestibles
            for( const auto &v : vitamin::all() ) {
                slot.default_nutrition.vitamins[ v.first ] += relative.get_int( "vitamins" );
            }
        } else if( relative.has_array( "vitamins" ) ) {
            for( JsonArray pair : relative.get_array( "vitamins" ) ) {
                vitamin_id vit( pair.get_string( 0 ) );
                slot.default_nutrition.vitamins[ vit ] += pair.get_int( 1 );
            }
        }
    '''


class UniqNameLoader(AbstractLoader):
    '''
    Uses name field as id
    '''
    id_field = 'name'


class AsIsLoader:
    '''
    For types that do not support copy-from field
    '''
    def load(self, obj):
        '''
        Return the object as-is
        '''
        return obj

    # def inherit(self, parent, child):
    #    '''
    #    Should never be called
    #    '''
    #    assert None


LOADERS = {
    'vehicle_part':     AbstractLoader,
    'monster':          AbstractLoader,
    'toolmod':          AbstractLoader,
    'generic':          AbstractLoader,
    'bionic_item':      AbstractLoader,
    'engine':           AbstractLoader,
    'tool':             AbstractLoader,
    'comestible':       AbstractLoader,
    'magazine':         AbstractLoader,
    'gun':              AbstractLoader,
    'book':             AbstractLoader,
    'pet_armor':        AbstractLoader,
    'armor':            AbstractLoader,
    'ammo':             AbstractLoader,
    'overmap_terrain':  EmptyIDLoader,
    'recipe':           RecipeLoader,
    'uncraft':          RecipeLoader,
    'monstergroup':     UniqNameLoader,
    'speech':           AsIsLoader,
    'rotatable_symbol': AsIsLoader,
    'profession_item_substitutions': AsIsLoader,
    'obsolete_terrain': AsIsLoader,
    'monster_faction':  AsIsLoader,
    'hit_range':        AsIsLoader,
    'dream':            AsIsLoader,
}


def fill_data(data):
    '''
    Main worker function
    '''
    to_fill = []
    skipped = []
    for obj in data:
        type_ = obj.get(LOADER_TYPE_FIELD)
        assert type_
        loader = LOADERS.get(type_, DefaultLoader)()
        if isinstance(loader, AsIsLoader):
            skipped.append(obj)
        else:
            to_fill += loader.load(obj)

    filled = inheritson.fill(
        to_fill,
        id_field=UNIQ_ID_FIELD,
        parent_id_field=PARENT_UNIQ_ID_FIELD,
        raise_orphans=False,
        preserve_order=True,
        inheritance_function=loader.inherit)  # FIXME: use relevant loaders

    return filled + skipped


if __name__ == '__main__':
    print(fill_data(import_data()[0]))
