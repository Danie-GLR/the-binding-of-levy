/**
 * Constants and configuration for The Binding of Levy
 */

export const CONFIG = {
    // Canvas settings
    CANVAS_WIDTH: 832,
    CANVAS_HEIGHT: 576,
    
    // Room settings
    ROOM_WIDTH: 832,
    ROOM_HEIGHT: 576,
    ROOM_PADDING: 100,
    
    // Player settings
    PLAYER_SIZE: 32,
    PLAYER_SPEED: 3.5,
    PLAYER_MAX_HEALTH: 6, // 3 hearts (2 health per heart)
    PLAYER_DAMAGE: 10,
    PLAYER_TEAR_SPEED: 7,
    PLAYER_TEAR_RANGE: 400,
    PLAYER_FIRE_RATE: 250, // milliseconds
    
    // Enemy settings
    ENEMY_SIZE: 32,
    ENEMY_SPEED: 1.5,
    ENEMY_HEALTH: 30,
    ENEMY_DAMAGE: 2,
    ENEMY_CHASE_RANGE: 300,
    ENEMY_ATTACK_RANGE: 40,
    
    // Boss settings
    BOSS_SIZE: 64,
    BOSS_HEALTH: 500,
    BOSS_DAMAGE: 4,
    BOSS_SPEED: 2,
    
    // Projectile settings
    TEAR_SIZE: 8,
    
    // Colors
    COLORS: {
        BACKGROUND: '#1a1410',
        FLOOR: '#2a2420',
        WALL: '#3a1810',
        DOOR: '#8b4513',
        PLAYER: '#ffeb3b',
        ENEMY: '#f44336',
        BOSS: '#9c27b0',
        TEAR: '#2196f3',
        ENEMY_PROJECTILE: '#ff5722',
        ITEM: '#4caf50',
        COIN: '#ffc107',
        BOMB: '#424242',
        KEY: '#ff9800',
        HEART: '#e91e63'
    },
    
    // Room types
    ROOM_TYPES: {
        START: 'start',
        NORMAL: 'normal',
        BOSS: 'boss',
        TREASURE: 'treasure',
        SHOP: 'shop',
        SECRET: 'secret',
        DEVIL: 'devil',
        ANGEL: 'angel'
    },
    
    // Item types
    ITEM_TYPES: {
        PASSIVE: 'passive',
        ACTIVE: 'active',
        TRINKET: 'trinket'
    },
    
    // Pickup types
    PICKUP_TYPES: {
        COIN: 'coin',
        BOMB: 'bomb',
        KEY: 'key',
        HEART: 'heart',
        SOUL_HEART: 'soul_heart'
    }
};

export const KEYS = {
    // Movement
    W: 'KeyW',
    A: 'KeyA',
    S: 'KeyS',
    D: 'KeyD',
    
    // Shooting
    ARROW_UP: 'ArrowUp',
    ARROW_DOWN: 'ArrowDown',
    ARROW_LEFT: 'ArrowLeft',
    ARROW_RIGHT: 'ArrowRight',
    
    // Actions
    SPACE: 'Space',
    E: 'KeyE',
    ESCAPE: 'Escape'
};
