/**
 * Item system - passive items, active items, and trinkets
 */

import { CONFIG } from './constants.js';

export class Item {
    constructor(name, type, description, effect) {
        this.name = name;
        this.type = type;
        this.description = description;
        this.effect = effect;
        this.x = 0;
        this.y = 0;
        this.width = 32;
        this.height = 32;
    }
    
    apply(player) {
        if (this.effect) {
            this.effect(player);
        }
    }
    
    render(ctx) {
        // Draw item pedestal
        ctx.fillStyle = '#8b4513';
        ctx.fillRect(this.x, this.y + 24, this.width, 8);
        
        // Draw item (placeholder)
        ctx.fillStyle = CONFIG.COLORS.ITEM;
        ctx.fillRect(this.x + 4, this.y, 24, 24);
    }
}

// Predefined items
export const ITEMS = {
    // Passive items
    SPEED_UP: new Item(
        'Speed Boost',
        CONFIG.ITEM_TYPES.PASSIVE,
        'Increases movement speed',
        (player) => {
            player.speed += 1;
        }
    ),
    
    DAMAGE_UP: new Item(
        'Damage Boost',
        CONFIG.ITEM_TYPES.PASSIVE,
        'Increases tear damage',
        (player) => {
            player.damage += 5;
        }
    ),
    
    HEALTH_UP: new Item(
        'Health Up',
        CONFIG.ITEM_TYPES.PASSIVE,
        'Adds one red heart container',
        (player) => {
            player.maxHealth += 2;
            player.health += 2;
        }
    ),
    
    FIRE_RATE_UP: new Item(
        'Fire Rate Up',
        CONFIG.ITEM_TYPES.PASSIVE,
        'Increases tear fire rate',
        (player) => {
            player.fireRate = Math.max(100, player.fireRate - 50);
        }
    ),
    
    RANGE_UP: new Item(
        'Range Up',
        CONFIG.ITEM_TYPES.PASSIVE,
        'Increases tear range',
        (player) => {
            player.tearRange += 100;
        }
    ),
    
    TRIPLE_SHOT: new Item(
        'Triple Shot',
        CONFIG.ITEM_TYPES.PASSIVE,
        'Shoot 3 tears at once',
        (player) => {
            const originalShoot = player.shoot.bind(player);
            player.shoot = function(direction) {
                originalShoot(direction);
                // Add two more tears at angles
                const angle = Math.atan2(direction.y, direction.x);
                const leftAngle = angle - Math.PI / 6;
                const rightAngle = angle + Math.PI / 6;
                originalShoot({ x: Math.cos(leftAngle), y: Math.sin(leftAngle) });
                originalShoot({ x: Math.cos(rightAngle), y: Math.sin(rightAngle) });
            };
        }
    ),
    
    SPECTRAL_TEARS: new Item(
        'Spectral Tears',
        CONFIG.ITEM_TYPES.PASSIVE,
        'Tears pass through enemies',
        (player) => {
            // Would need to modify tear collision logic
            player.damage += 2;
        }
    ),
    
    // Active items
    BOOK_OF_DOOM: new Item(
        'Book of Doom',
        CONFIG.ITEM_TYPES.ACTIVE,
        'Damages all enemies in the room',
        null // Active items have different usage pattern
    ),
    
    TELEPORT: new Item(
        'Teleport',
        CONFIG.ITEM_TYPES.ACTIVE,
        'Teleports to a random room',
        null
    )
};

// Get random passive item
export function getRandomPassiveItem() {
    const passiveItems = Object.values(ITEMS).filter(
        item => item.type === CONFIG.ITEM_TYPES.PASSIVE
    );
    return passiveItems[Math.floor(Math.random() * passiveItems.length)];
}

// Get random active item
export function getRandomActiveItem() {
    const activeItems = Object.values(ITEMS).filter(
        item => item.type === CONFIG.ITEM_TYPES.ACTIVE
    );
    return activeItems[Math.floor(Math.random() * activeItems.length)];
}
