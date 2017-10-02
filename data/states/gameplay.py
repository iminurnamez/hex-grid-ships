import pygame as pg

from .. import tools, prepare
from ..components.labels import Label
from ..components.hexgrid import HexMap, MerchantShip


class InfoWindow(pg.sprite.Sprite):
    def __init__(self, pos):
        super(InfoWindow, self).__init__()
        self.rect = pg.Rect
        x, y = pos
        if x >= prepare.SCREEN_RECT.w // 2:
            offx = -160
        elif x < prepare.SCREEN_RECT.w // 2:
            offx = 32
        if y >= 256:
            offy = -160
        else:
            offy = 64
        self.rect = pg.Rect(x + offx, y + offy, 128, 128)
        self.image = pg.Surface(self.rect.size)
        self.image.fill(pg.Color("gray20"))


class ShipWindow(InfoWindow):
    def __init__(self, ship, mouse_pos):
        super(ShipWindow, self).__init__(mouse_pos)
        self.make_labels(ship)

    def make_labels(self, ship):
        labels = pg.sprite.Group()
        Label("Merchant Ship", {"midtop": (self.rect.w//2, 0)}, labels, font_size=14)
        top = 16
        for good, amt in ship.cargo.items():
            Label(good.title(), {"topleft": (16, top)}, labels, font_size=12)
            Label("{}".format(amt), {"topleft": (64, top)}, labels, font_size=12)
            top += 16
        labels.draw(self.image)

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class TerrainWindow(InfoWindow):
    def __init__(self, cell, mouse_pos):
        super(TerrainWindow, self).__init__(mouse_pos)
        self.make_labels(cell)

    def make_labels(self, cell):
        labels = pg.sprite.Group()
        Label(cell.terrain.title(), {"midtop": (self.rect.w//2, 0)}, labels, font_size=14)
        if cell.terrain == "port":
            top = 16
            for good, amt in cell.island.inventory.items():
                Label(good.title(), {"topleft": (16, top)}, labels, font_size=12)
                Label("{}".format(amt), {"topleft": (64, top)}, labels, font_size=12)
                top += 16
        elif cell.terrain == "ocean":
            pass
        else:
            top = 16
            Label("Produces {}".format(cell.island.terrain_products[cell.terrain].title()),
                    {"midtop": (self.rect.w//2, top)}, labels, font_size=12)
            top += 24
            Label("Workers", {"topleft": (16, top)}, labels, font_size=12)
            Label("{}".format(cell.workers), {"topleft": (80, top)}, labels, font_size=12)
        labels.draw(self.image)

    def draw(self, surface):
        surface.blit(self.image, self.rect)


class Cursor(pg.sprite.Sprite):
    def __init__(self):
        super(Cursor, self).__init__()
        self.image = pg.Surface((2, 2)).convert_alpha()
        self.image.fill(pg.Color("white"))
        self.rect = self.image.get_rect()
        self.mask = pg.mask.from_surface(self.image)


class Gameplay(tools._State):
    def __init__(self):
        super(Gameplay, self).__init__()
        self.hexmap = HexMap(30, 40, (64, 64))
        self.hexmap.make_surface()
        self.topleft = (0, 0)
        self.scroll_speed = 4
        self.cursor = Cursor()
        self.window = None
        self.running = True
        self.zoom_level = 1
        self.zoom_size = prepare.SCREEN_SIZE

    def startup(self, persistent):
        self.persist = persistent

    def get_event(self,event):
        if event.type == pg.QUIT:
            self.quit = True
        elif event.type == pg.KEYUP:
            if event.key == pg.K_ESCAPE:
                self.quit = True
            elif event.key == pg.K_SPACE:
                self.running = not self.running
        elif event.type == pg.MOUSEBUTTONUP:
            if event.button == 1:
                self.window = None
                for ship in self.hexmap.ships:
                    if pg.sprite.collide_mask(ship, self.cursor):
                        self.window = ShipWindow(ship, event.pos)
                        break
            elif event.button == 3:
                self.window = None
                for cell in self.hexmap.grid.values():
                    if pg.sprite.collide_mask(cell, self.cursor):
                        self.window = TerrainWindow(cell, event.pos)
                        break
            elif event.button == 4:
                self.zoom_in()
            elif event.button == 5:
                self.zoom_out()

    def zoom_in(self):
        self.zoom_level += 1
        w, h = prepare.SCREEN_SIZE
        self.zoom_size = w // self.zoom_level, h // self.zoom_level


    def zoom_out(self):
        self.zoom_level -= 1
        if self.zoom_level < 1:
            self.zoom_level = 1
        w, h = prepare.SCREEN_SIZE
        self.zoom_size = w // self.zoom_level, h // self.zoom_level

    def scroll(self, mouse_pos):
        mx, my = mouse_pos
        if mx < 16 and self.topleft[0] > 0:
            self.topleft = self.topleft[0] - self.scroll_speed, self.topleft[1]
        elif mx > prepare.SCREEN_RECT.right - 16 and self.topleft[0] < self.hexmap.image.get_width() - prepare.SCREEN_RECT.w:
            self.topleft = self.topleft[0] + self.scroll_speed, self.topleft[1]
        if my < 16 and self.topleft[1] > 0:
            self.topleft = self.topleft[0], self.topleft[1] - self.scroll_speed
        elif my > prepare.SCREEN_RECT.bottom - 16 and self.topleft[1] < self.hexmap.image.get_height() - prepare.SCREEN_RECT.h:
            self.topleft = self.topleft[0], self.topleft[1] + self.scroll_speed

    def update(self, dt):
        mouse_pos = pg.mouse.get_pos()
        self.cursor.rect.topleft = (mouse_pos[0] // self.zoom_level) + self.topleft[0], (mouse_pos[1] // self.zoom_level) + self.topleft[1]
        self.scroll(mouse_pos)
        if self.running:
            self.hexmap.update(dt)

        surf = self.hexmap.image.copy()
        for ship in self.hexmap.ships:
            ship.draw(surf)
        self.image = surf.subsurface(self.topleft, self.zoom_size)
        if self.zoom_level != 1:
            self.image = pg.transform.scale(self.image, prepare.SCREEN_SIZE)

    def draw(self, surface):
        surface.blit(self.image, (0, 0))
        if self.window is not None:
            self.window.draw(surface)


