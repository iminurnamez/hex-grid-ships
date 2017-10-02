from random import choice, sample, randint, shuffle
from itertools import cycle

import pygame as pg

from .. import prepare
from ..components.labels import Label
from ..components.animation import Animation, Task

class HexCell(pg.sprite.Sprite):
    def __init__(self, index, rect, terrain):
        super(HexCell, self).__init__()
        self.index = index
        self.rect = rect
        self.outline_rect = self.rect.inflate(8, 8)
        self.set_terrain(terrain)
        self.workers = 0
        self.mask = pg.mask.from_surface(self.image)
        self.inventory = {
                "Gold": 0,
                "Iron": 0,
                "Wood": 0,
                "Crops": 0,
                "Fish": 0}

    def set_terrain(self, terrain):
        self.terrain = terrain
        self.image = prepare.GFX["hex-{}".format(terrain)]
        self.outline_img = prepare.GFX["outline-generic"]

    def get_neighbors(self, grid):
        offset_indices = {
            0: [(-1, 0), (-1, -1), (0, -1), (1, 0), (0, 1), (-1, 1)],
            1: [(-1, 0), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1)]}
        offsets = offset_indices[self.index[1] % 2]
        neighbors = []
        for off in offsets:
            try:
                n = grid[(off[0] + self.index[0], off[1] + self.index[1])]
                neighbors.append(n)
            except KeyError:
                pass
        return neighbors

        
class Economy(object):
    def __init__(self):
        self.base_prices = {
            "Gold": 10,
            "Iron": 5,
            "Wood": 3,
            "Crops": 2,
            "Fish": 1}
        self.per_cap_consumption = {
            "Gold": .05,
            "Iron": .1,
            "Wood": .2,
            "Crops": .25,
            "Fish": .25}
        self.per_cap_production = {
            "Gold": 1,
            "Iron": 1,
            "Wood": 1,
            "Crops": 1,
            "Fish": 1}
        
    def calc_price(self, item, supply, demand):
        mod = demand / float(supply)
        return self.base_prices[item] * mod
        
        
class MerchantShip(pg.sprite.Sprite):
    masks = {x: pg.mask.from_surface(prepare.GFX["ship-{}".format(x)])
                  for x in ("e","w","ne","nw","se", "sw")}
    directions = {
        0: {
            (1, 0): "e",
            (-1, 0): "w",
            (0, 1): "se",
            (0, -1): "ne",
            (-1, 1): "sw",
            (-1, -1): "nw"},
        1: {
            (-1, 0): "w",        
            (1, 0): "e",        
            (1, 1): "se",        
            (0, 1): "sw",        
            (0, -1): "nw",        
            (1, -1): "ne"}}
            
    def __init__(self, home_port, away_port, hex_grid, economy):
        super(MerchantShip, self).__init__()
        self.animations = pg.sprite.Group()
        self.cargo = {
            "Gold": 0,
            "Iron": 0,
            "Wood": 0,
            "Crops": 0,
            "Fish": 0}
        self.cargo_capacity = 50
        self.home_port = home_port
        self.away_port = away_port
        route_to = hex_grid.get_path(self.home_port, self.away_port, ["ocean", "shallows"])
        route_back = route_to[1:-1][::-1]
        route = route_to + route_back
        self.route = []
        start = route[-1]
        for i, r in enumerate(route):
            dest = r
            dx = dest.index[0] - start.index[0]
            dy = dest.index[1] - start.index[1]            
            direction = self.directions[start.index[1] % 2][(dx, dy)]
            self.route.append((dest, direction))
            start = r
        begin_direct = self.route[0][1]
        self.route = cycle(self.route)        
        self.image = prepare.GFX["ship-{}".format(begin_direct)]
        self.mask = self.masks[begin_direct]
        self.rect = self.image.get_rect(center=self.home_port.rect.center)
        self.port_is_destination = False
        self.next_port = None
        next(self.route)
        self.set_next_destination(economy)

    def set_next_destination(self, economy):
        if self.port_is_destination:
            self.port_call(self.next_port.island, economy)
            self.port_is_destination = False
        destination, direction = next(self.route)
        if destination.terrain == "port":
            self.port_is_destination = True
            self.next_port = destination            
        self.image = prepare.GFX["ship-{}".format(direction)]
        self.mask = self.masks[direction]
        ani = Animation(left=destination.rect.left, top=destination.rect.top, duration=1000)
        ani.start(self.rect)
        self.animations.add(ani)
        
    def port_call(self, island, economy):
        for c in self.cargo:
            island.inventory[c] += self.cargo[c]
            self.cargo[c] = 0
        products = island.inventory.keys()
        shuffle(products)
        for product in products:
            need = island.population * economy.per_cap_consumption[product] * 14
            if island.inventory[product] > need:
                capacity = self.cargo_capacity - sum(self.cargo.values())
                amt = min(island.inventory[product] - need, capacity)
                self.cargo[product] += amt
                island.inventory[product] -= amt
            
        
    def update(self, dt, economy):
        self.animations.update(dt)
        if not self.animations:
            self.set_next_destination(economy)
        
    def draw(self, surface):
        surface.blit(self.image, self.rect)
        
    
class Island(object):
    terrain_products = {
        "mountains": "Gold",
        "hills": "Iron",
        "jungle": "Wood",
        "plains": "Crops",
        "shallows": "Fish"}
        
    def __init__(self, cells):
        self.inventory = {
            "Gold": 0,
            "Iron": 0,
            "Wood": 0,
            "Crops": 0,
            "Fish": 0}
        self.cells = cells
        for c in self.cells:
            c.island = self
        self.population = randint(5, 15)
        self.working_cells = [x for x in self.cells if not x.terrain == "port"]
        self.port = [x for x in self.cells if x not in self.working_cells][0]
        self.assign_workers()
        
    def assign_workers(self):
        for _ in range(self.population):
            cell = choice(self.working_cells)
            cell.workers += 1
            
    def calc_consumption(self, economy):
        return {x: self.population * economy.per_cap_consumption[x]
                    for x in economy.per_cap_consumption}
        
    def calc_production(self):
        production = {
            "Gold": 0,
            "Iron": 0,
            "Wood": 0,
            "Crops": 0,
            "Fish": 0}
        for cell in self.working_cells:
            product = self.terrain_products[cell.terrain]
            production[product] += cell.workers 
        return production            
        
    def update(self, economy):
        production = self.calc_production()
        for product in production:
            self.inventory[product] += production[product]
        consumption = self.calc_consumption(economy)
        for p in consumption:
            self.inventory[p] -= consumption[p]
            if self.inventory[p] < 0:
                self.inventory[p] = 0
           
    
class HexMap(object):
    def __init__(self, num_rows, num_columns, cell_size):
        self.num_rows = num_rows
        self.num_columns = num_columns
        self.cell_size = cell_size
        self.make_grid()
        num_continents = randint(4, 7)
        self.continents = self.make_continents(num_continents)
        
        self.make_coastlines()
        self.islands = [Island(continent) for continent in self.continents]
        self.topleft = (0, 0)
        self.economy = Economy()
        self.make_ships()
        self.day_length = 2000
        self.day_timer = 0
        for _ in range(100):
            for island in self.islands:
                island.update(self.economy)

    def update(self, dt):
        self.day_timer += dt
        if self.day_timer >= self.day_length:
            self.day_timer -= self.day_length
            for island in self.islands:
                island.update(self.economy)
        for ship in self.ships:
            ship.update(dt, self.economy)    
       
    def make_ships(self):
        self.ships = []
        for port in self.ports:
            other_ports = [x for x in self.ports if x != port]
            for other in other_ports:
                ship = MerchantShip(port, other, self, self.economy)
                self.ships.append(ship)    

    def make_grid(self):
        row_offset = 32
        column_offset = 48
        w, h  = self.cell_size
        self.grid = {}
        for y in range(self.num_rows):
            for x in range(self.num_columns):
                left = (row_offset * (y%2)) + (w * x)
                top = (column_offset * y)
                rect = pg.Rect(left, top, w, h)
                self.grid[(x, y)] = HexCell((x, y), rect, "ocean")
    
    def get_continent_spots(self, num_continents):
        xes = range(3, self.num_columns - 3)
        ys = range(3, self.num_rows - 3)
        spots = [(x, y) for x in xes for y in ys]
        return sample(spots, num_continents)

    def make_continents(self, num_continents):
        spots = self.get_continent_spots(num_continents)
        continents = []
        for spot in spots:
            continent = []
            num_cells = randint(5, 15)
            num_mountains = randint(0, 2)
            if num_mountains:
                self.grid[spot].set_terrain("mountains")
                continent.append(self.grid[spot])
                neighbors = [x for x in self.grid[spot].get_neighbors(self.grid) if x not in continent]
                for _ in range(num_mountains - 1):
                    s = choice(neighbors)
                    s.set_terrain("mountains")
                    continent.append(s)
                    neighbors = [x for x in s.get_neighbors(self.grid) if x not in continent]
                hills = []
                for m in continent:
                    neighbors_ = [x for x in m.get_neighbors(self.grid) if x not in continent and x not in hills]
                    for n_ in neighbors_:
                        n_.set_terrain("hills")
                        hills.append(n_)
                continent.extend(hills)
            else:
                self.grid[spot].set_terrain("jungle")
                continent.append(self.grid[spot])
            for m_ in [x for x in continent if x.terrain in ["hills", "jungle"]]:
                neighb = [x for x in m_.get_neighbors(self.grid) if x not in continent and x.terrain == "ocean"]
                for neigh in neighb:
                    neigh.set_terrain("jungle")
                    continent.append(neigh)
                    
            cells_left = num_cells
            starts = [x for x in continent if x.terrain in ("jungle", "hills")]
            attempts = 0
            while cells_left and attempts < 200:
                attempts += 1
                expander = choice(starts)
                possible = [t for t in expander.get_neighbors(self.grid) if t.terrain == "ocean"]
                if possible:
                    expand = choice(possible)
                    expand.set_terrain(choice(["plains", "jungle"]))
                    continent.append(expand)
                    cells_left -= 1
                    starts.append(expand) 
            continents.append(continent)
        return continents
        
    def make_coastlines(self):
        self.ports = []
        for continent in self.continents:
            port_added = False
            coast = []
            for cell in continent:
                for n in cell.get_neighbors(self.grid):  
                    if n.terrain == "ocean":
                        if cell.terrain == "plains" and not port_added:
                            cell.set_terrain("port")
                            port_added = True
                            self.ports.append(cell)
                        n.set_terrain("shallows")
                        coast.append(n)
            continent.extend(coast)            
            
    def make_surface(self):
        surf = pg.Surface((self.num_columns * self.cell_size[0], int( (self.num_rows // 2) * self.cell_size[1] * 1.5)))
        for cell in self.grid.values():
            surf.blit(cell.image, cell.rect)
            surf.blit(cell.outline_img, cell.rect)
        self.image = surf

    def find_path_to(self, origin, destination, valid_terrains):
        origin = origin
        destination = destination
        visited = set()
        levels = [[(origin, origin)]]
        while True:
            neighbors = []
            for cell, parent in levels[-1]:
                candidates = cell.get_neighbors(self.grid)
                for c in candidates:
                    if c == destination:
                        levels.append([(c, cell)])
                        return levels
                    if c not in visited and c.terrain in valid_terrains:
                        neighbors.append((c, cell))
                    visited.add(c)
            if neighbors:
                levels.append(neighbors)
            else:
                return None

    def backtrack(self, path_cells):
        dest = path_cells[-1][0][0]
        route =[dest]
        for level in path_cells[::-1]:
            for cell, parent in level:
                if parent == path_cells[0][0][0]:
                    route.append(parent)
                    return route[::-1]
                if cell == route[-1]:
                    route.append(parent)
                    break

    def get_path(self, origin, destination, valid_terrains):
        to = self.find_path_to(origin, destination, valid_terrains)
        if to:
            return self.backtrack(to)
