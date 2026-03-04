# The Binding of Levy

A roguelike action-adventure game inspired by *The Binding of Isaac*, built with HTML5, CSS3, and JavaScript.

## 🎮 Game Features

### Core Mechanics
- **Procedurally Generated Dungeons**: Every playthrough is unique with randomized room layouts, enemy placements, and item spawns
- **Twin-Stick Shooter Gameplay**: Move with WASD, shoot tears in 8 directions with arrow keys
- **Room Variety**: Start rooms, normal rooms, treasure rooms, boss rooms, and more
- **Enemy AI**: Different enemy types with unique behaviors and attack patterns
- **Boss Fights**: Challenging boss encounters with multiple phases
- **Item System**: Collect passive items, active items, and trinkets that modify gameplay
- **Health System**: Heart-based health with red hearts and soul hearts
- **Resource Management**: Bombs, keys, and coins to collect and manage

### Game Elements

#### Player Character
- Movement with WASD keys
- Shoot tears in 8 directions using arrow keys (including diagonals)
- Health represented by hearts (3 red hearts to start)
- Invincibility frames after taking damage
- Inventory for bombs, keys, and coins

#### Enemies
- **Basic Enemies**: Chase the player within range
- **Fly Enemies**: Faster, weaker flying enemies
- **Bosses**: Large enemies with high health and unique attack patterns

#### Room Types
- **Start Room**: Safe spawn point with no enemies
- **Normal Room**: Contains random enemies
- **Boss Room**: Contains a boss fight
- **Treasure Room**: Contains special items

#### Items & Pickups
- **Coins** 💰: Currency for shops
- **Bombs** 💣: Explosive items for destroying obstacles
- **Keys** 🔑: Open locked doors and treasure rooms
- **Hearts** ❤️: Restore health
- **Soul Hearts** 💙: Add extra health containers

#### Passive Items
- Speed Boost: Increases movement speed
- Damage Boost: Increases tear damage
- Health Up: Adds heart containers
- Fire Rate Up: Shoot tears faster
- Range Up: Tears travel farther
- Triple Shot: Shoot 3 tears at once
- And many more!

## 🎯 How to Play

### Controls
- **WASD** - Move your character
- **Arrow Keys** - Shoot tears (supports 8 directions including diagonals)
- **Space** - Use active item
- **E** - Place bomb
- **ESC** - Pause game

### Objective
1. Navigate through procedurally generated rooms
2. Defeat all enemies in each room to unlock doors
3. Collect items to power up your character
4. Reach and defeat the boss to progress to the next floor
5. Survive as long as possible!

## 🚀 Getting Started

### Playing the Game

Simply open `index.html` in a modern web browser:

```bash
# If you have a local server (recommended):
python -m http.server 8000
# Or
npx serve

# Then open http://localhost:8000 in your browser
```

Or just double-click `index.html` to play directly in your browser!

### Requirements
- Modern web browser with HTML5 Canvas support
- Keyboard for controls
- No installation or dependencies required!

## 📁 Project Structure

```
the-binding-of-levy/
├── index.html              # Main HTML file
├── styles.css             # Game styling
├── js/
│   ├── main.js           # Entry point and menu management
│   ├── game.js           # Main game loop and logic
│   ├── constants.js      # Game configuration and constants
│   ├── input.js          # Keyboard input handling
│   ├── player.js         # Player character logic
│   ├── enemy.js          # Enemy classes and AI
│   ├── projectile.js     # Tear projectiles
│   ├── room.js           # Individual room logic
│   ├── dungeon.js        # Procedural dungeon generation
│   ├── pickup.js         # Collectible items (coins, hearts, etc.)
│   ├── item.js           # Power-up items and effects
│   └── ui.js             # HUD and UI management
└── README.md             # This file
```

## 🎨 Game Design

### Inspired By
This game draws heavy inspiration from *The Binding of Isaac* by Edmund McMillen, incorporating elements from:
- Roguelike dungeon crawlers
- Twin-stick shooters
- Bullet-hell games
- Dark fantasy aesthetics

### Technical Implementation
- **Pure JavaScript**: No frameworks or libraries required
- **HTML5 Canvas**: 2D rendering with canvas API
- **Object-Oriented Design**: Modular class-based architecture
- **Procedural Generation**: Algorithm-based dungeon creation
- **State Management**: Clean state transitions between menus and gameplay

## 🔧 Customization

You can easily modify game parameters in `js/constants.js`:

```javascript
// Adjust player stats
PLAYER_SPEED: 3.5
PLAYER_MAX_HEALTH: 6
PLAYER_DAMAGE: 10

// Modify enemy difficulty
ENEMY_SPEED: 1.5
ENEMY_HEALTH: 30

// Change room generation
ROOM_WIDTH: 832
ROOM_HEIGHT: 576
```

## 🎯 Future Enhancements

Potential features to add:
- [ ] More enemy types and bosses
- [ ] Additional room types (shops, devil rooms, angel rooms)
- [ ] More items with synergies
- [ ] Sound effects and music
- [ ] Particle effects and animations
- [ ] Character selection
- [ ] Achievement system
- [ ] Seeded runs
- [ ] Hard mode
- [ ] Co-op multiplayer

## 🐛 Known Issues

- Boss AI patterns are basic and can be expanded
- No wall collision for enemies (they can overlap walls)
- Item synergies are limited
- No persistent save system

## 📝 License

This is a fan project inspired by The Binding of Isaac. All rights to the original game belong to Edmund McMillen and Nicalis.

## 🙏 Credits

- Original Game Concept: Edmund McMillen
- Implementation: Fan Project
- Built with: HTML5, CSS3, JavaScript

---

**Enjoy playing The Binding of Levy!** 🎮
