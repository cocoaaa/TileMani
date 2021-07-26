#spacenet data preprocessing global variables
import numpy as np
from Road import *

# Road type value definition
## Defined as enum in class Road
# MOTORWAY = 1
# PRIMARY = 2
# SECONDARY = 3
# TERTIARY = 4
# RESIDENTIAL = 5
# UNCLASSIFIED = 6
# CART = 7

G_NUMERIC_COLS = ['bridge_type',
 'lane_number',
 'one_way_type',
 'paved',
 'road_id',
 'road_type']

G_COLS = ['bridge_type',
 'heading',
 'lane_numbe',
 'lane_number',
 'one_way_type',
 'paved',
 'road_id',
 'road_type',
 'origarea',
 'origlen',
 'partialDec',
 'truncated',
 'geometry']


# road_type to width mapping
# G_WIDTHS = {Road.Motorway: 3.5,
#             Road.Primary: 3.5,
#             Road.Secondary: 3.,
#             Road.Tertiary: 3.,
#             Road.Residential: 3.,
#             Road.Unclassified: 3.,
#             Road.Cart: 3.,
#             }
G_WIDTHS = {Road.Motorway.value: 3.5,
            Road.Primary.value: 3.5,
            Road.Secondary.value: 3.,
            Road.Tertiary.value: 3.,
            Road.Residential.value: 3.,
            Road.Unclassified.value: 3.,
            Road.Cart.value: 3.,
            }

G_DROP_COLS = ['heading', 
               'lane_numbe', 
               'origarea', 
               'origlen', 
               'partialDec', 
               'truncated']

G_GEOM_COLS = ['geometry', 
              'buff_geo']

## For OSM Road data
OSM_ROAD_DROP_COLS = ['name', 
                      'waterway', 
                      'aerialway', 
                      'barrier', 
                      'man_made', 
                      'z_order', 
                      'other_tags']
