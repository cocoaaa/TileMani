from enum import IntEnum
from typing import Dict


G_RTS = [
    # roads
    'motorway', 'trunk', 'primary',
    'secondary', 'tertiary', 'unclassified',
    'residential',

    # links
    # 'motorway_link', 'trunk_link', 'primary_link',
    # 'secondary_link', 'tertiary_link',

    # special types
    'service',

    # all others
    'others'
]

G_RT_COLORS = {
    "motorway": 'r',
    "trunk": 'orangered',
    "primary": 'daskorange',
    "secondary": 'orange',
    "tertiary": 'yellow',
    "unclassified": 'greenyellow',
    "residential": 'cyan',
    "service": "brown",
    "others": "gray"
}


def rt2color(rt: str,
             rt_colors: Dict = None,
             link_color: str = "magenta",
             default_color: str = "gray"):
    rt = rt.lower()

    color = default_color
    if rt.endswith("link"):
        color = link_color

    else:
        try:
            color = G_RT_COLORS[rt]
        except KeyError:
            pass
    return color


class Road(IntEnum):
    #todo remove later
    MOTORWAY = 1
    PRIMARY = 2
    SECONDARY = 3
    TERTIARY = 4
    RESIDENTIAL = 5
    UNCLASSIFIED = 6
    CART = 7

    def describe(self):
        return (self.name, self.value)


class RoadType(IntEnum):
    # TODO
    MAJOR = 1
    MINOR = 2
    OTHER = 3

    def describe(self):
        return (self.name, self.value)
    

G_RWIDTHS = {Road.MOTORWAY: 3.5,
            Road.PRIMARY: 3.5,
            Road.SECONDARY: 3.,
            Road.TERTIARY: 3.,
            Road.RESIDENTIAL: 3.,
            Road.UNCLASSIFIED: 3.,
            Road.CART: 3.,
            }
################################################################################
## Spacenet Road Type
################################################################################
class SpacenetRoad(IntEnum):
    MOTORWAY = 1
    PRIMARY = 2
    SECONDARY = 3
    TERTIARY = 4
    RESIDENTIAL = 5
    UNCLASSIFIED = 6
    CART = 7
    
    @classmethod
    def radius_mapping(cls):
        rmap = {
            cls.MOTORWAY: 3.5/2,
            cls.PRIMARY: 3.5/2,
            cls.SECONDARY: 3./2,
            cls.TERTIARY: 3./2,
            cls.RESIDENTIAL: 3./2,
            cls.UNCLASSIFIED: 3./2,
            cls.CART: 3./2,
            }
        return rmap

    def get_radius(self):
        return SpacenetRoad.radius_mapping()[self]
    
    def describe(self):
        return (self.name, self.value)
    
    
    def to_global(self):
        #todo: refer to the mapping defined in World Food Program pdf
        if self in [SpacenetRoad.MOTORWAY,SpacenetRoad.PRIMARY, SpacenetRoad.SECONDARY, 
                    SpacenetRoad.TERTIARY, SpacenetRoad.UNCLASSIFIED]: #[1,2,3,4,6]:
            return RoadType.MAJOR
        
        elif self in [SpacenetRoad.RESIDENTIAL]:
            return RoadType.MINOR
        else:
            return RoadType.OTHER


################################################################################
## OSM Road Type
################################################################################
_osm_rtypes = ['bridleway',
'cycleway',
'footway',
'living_street',
'motorway',
'motorway_link',
'path',
'pedestrian',
'primary',
'raceway',
'residential',
'road',
'secondary',
'secondary_link',
'service',
'steps',
'tertiary',
'tertiary_link',
'track',
'trunk',
'trunk_link',
'unclassified']

_osm_rtypes_str = ' '. join(list(map(lambda x: x.upper(), _osm_rtypes)))
# print(_osm_rtypes_str)

#todo: remap this based on the WFP pdf
def r_osm2spacenet(osmroad_type):

    """osm_roadtype to spacenet_roadtype mapping"""
    spacenet_type = None
    if osmroad_type.name in ['MOTORWAY', 'MOTORWAY_LINK']:
        spacenet_type = SpacenetRoad['MOTORWAY']
    elif osmroad_type.name in ['PRIMARY', 'TRUNK', 'TRUNK_LINK']:
        spacenet_type = SpacenetRoad['PRIMARY']
    elif osmroad_type.name in ['SECONDARY', 'SECONDARY_LINK']:
        spacenet_type = SpacenetRoad['SECONDARY']
    elif osmroad_type.name in ['TERTIARY', 'TERTIARY_LINK']:
        spacenet_type = SpacenetRoad['TERTIARY']
    elif osmroad_type.name in ['CYCLEWAY', 'FOOTWAY', 'LIVING_STREET', 'PEDESTRIAN',
                               'RESIDENTIAL', 'SERVICE']:
        spacenet_type = SpacenetRoad['RESIDENTIAL']
    elif osmroad_type.name in ['UNCLASSIFIED']:
        spacenet_type = SpacenetRoad['UNCLASSIFIED']
    elif osmroad_type.name in ['PATH']:
        spacenet_type = SpacenetRoad['CART']
    else:
        print("This osm_rtype is not mapped to any spacenet_rtype: {}".
              format(osmroad_type.name) )
        print(" For now we assign None")
    return spacenet_type

@staticmethod
def __osm_radius_per_lane():
    return 1.8

@staticmethod
def __osm_default_lane_nums():
    return 1.0

# def get


## todo: use add_method(cls) decorator
## https://medium.com/@mgarod/dynamically-add-a-method-to-a-class-in-python-c49204b85bd6
OSMRoad = IntEnum('OSMRoad', _osm_rtypes_str)
setattr(OSMRoad, 'describe', lambda self: (self.name, self.value) )
setattr(OSMRoad, 'to_spacenet_rtype', lambda self: r_osm2spacenet(self))
setattr(OSMRoad, 'radius_per_lane', __osm_radius_per_lane)
setattr(OSMRoad, 'default_lane_nums', __osm_default_lane_nums)


################################################################################
## Tests
################################################################################
def test_road_enum():
    moto_type = Road.MOTORWAY
    print(moto_type)
    moto_type.describe()
    
def test_osmroad_enum():
    for r in OSMRoad:
        print(r.describe())
    
    for r in OSMRoad:
        print(r.name, " --> ", r.to_spacenet_rtype().name)
        
def test_mapping():
    for osm_rtype in OSMRoad:
        print(osm_rtype, "-->", osm_rtype.to_spacenet_rtype())
    
if __name__ == '__main__':
#     test_road_enum()
    test_mapping()
