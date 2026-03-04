/**
 * Room class - represents a single room in the dungeon
 */

import { CONFIG } from './constants.js';
import { Enemy, FlyEnemy, Boss } from './enemy.js';
import { Pickup } from './pickup.js';

export class Room {
    constructor(x, y, type = CONFIG.ROOM_TYPES.NORMAL) {
        this.gridX = x;
        this.gridY = y;
        this.type = type;
        
        // Room state
        this.visited = false;
        this.cleared = false;
        this.doorsOpened = false;
        
        // Doors (connections to other rooms)
        this.doors = {
            top: false,
            bottom: false,
            left: false,
            right: false
        };
        
        // Entities in room
        this.enemies = [];
        this.pickups = [];
        this.items = [];
        
        // Generate room content
        this.generate();
    }
    
    generate() {
        // Generate enemies based on room type
        if (this.type === CONFIG.ROOM_TYPES.NORMAL) {
            const enemyCount = Math.floor(Math.random() * 4) + 2;
            for (let i = 0; i < enemyCount; i++) {
                const x = CONFIG.ROOM_PADDING + Math.random() * (CONFIG.CANVAS_WIDTH - CONFIG.ROOM_PADDING * 2 - 32);
                const y = CONFIG.ROOM_PADDING + Math.random() * (CONFIG.CANVAS_HEIGHT - CONFIG.ROOM_PADDING * 2 - 32);
                
                // Random enemy type
                if (Math.random() < 0.3) {
                    this.enemies.push(new FlyEnemy(x, y));
                } else {
                    this.enemies.push(new Enemy(x, y));
                }
            }
        } else if (this.type === CONFIG.ROOM_TYPES.BOSS) {
            const x = CONFIG.CANVAS_WIDTH / 2 - CONFIG.BOSS_SIZE / 2;
            const y = CONFIG.CANVAS_HEIGHT / 2 - CONFIG.BOSS_SIZE / 2;
            this.enemies.push(new Boss(x, y));
        } else if (this.type === CONFIG.ROOM_TYPES.TREASURE) {
            // Spawn a treasure item
            const x = CONFIG.CANVAS_WIDTH / 2 - 16;
            const y = CONFIG.CANVAS_HEIGHT / 2 - 16;
            // TODO: Add actual item system
            this.pickups.push(new Pickup(x, y, CONFIG.PICKUP_TYPES.SOUL_HEART));
        }
        
        // Start room has no enemies and doors open
        if (this.type === CONFIG.ROOM_TYPES.START) {
            this.cleared = true;
            this.doorsOpened = true;
        }
    }
    
    update(dt, player) {
        // Mark as visited
        if (!this.visited) {
            this.visited = true;
        }
        
        // Update enemies
        this.enemies = this.enemies.filter(enemy => !enemy.destroyed);
        this.enemies.forEach(enemy => enemy.update(dt, player));
        
        // Update pickups
        this.pickups = this.pickups.filter(pickup => !pickup.destroyed);
        this.pickups.forEach(pickup => pickup.update(dt));
        
        // Check if room is cleared
        if (!this.cleared && this.enemies.length === 0 && this.type !== CONFIG.ROOM_TYPES.START) {
            this.cleared = true;
        }
    }
    
    render(ctx) {
        // Draw floor
        ctx.fillStyle = CONFIG.COLORS.FLOOR;
        ctx.fillRect(
            CONFIG.ROOM_PADDING,
            CONFIG.ROOM_PADDING,
            CONFIG.CANVAS_WIDTH - CONFIG.ROOM_PADDING * 2,
            CONFIG.CANVAS_HEIGHT - CONFIG.ROOM_PADDING * 2
        );
        
        // Draw walls
        ctx.fillStyle = CONFIG.COLORS.WALL;
        // Top wall
        ctx.fillRect(0, 0, CONFIG.CANVAS_WIDTH, CONFIG.ROOM_PADDING);
        // Bottom wall
        ctx.fillRect(0, CONFIG.CANVAS_HEIGHT - CONFIG.ROOM_PADDING, CONFIG.CANVAS_WIDTH, CONFIG.ROOM_PADDING);
        // Left wall
        ctx.fillRect(0, 0, CONFIG.ROOM_PADDING, CONFIG.CANVAS_HEIGHT);
        // Right wall
        ctx.fillRect(CONFIG.CANVAS_WIDTH - CONFIG.ROOM_PADDING, 0, CONFIG.ROOM_PADDING, CONFIG.CANVAS_HEIGHT);
        
        // Draw doors
        this.renderDoors(ctx);
        
        // Draw pickups
        this.pickups.forEach(pickup => pickup.render(ctx));
        
        // Draw enemies
        this.enemies.forEach(enemy => enemy.render(ctx));
    }
    
    renderDoors(ctx) {
        const doorWidth = 80;
        const doorHeight = 40;
        const doorColor = this.doorsOpened ? CONFIG.COLORS.DOOR : '#000';
        
        // Top door
        if (this.doors.top) {
            ctx.fillStyle = doorColor;
            ctx.fillRect(
                CONFIG.CANVAS_WIDTH / 2 - doorWidth / 2,
                0,
                doorWidth,
                CONFIG.ROOM_PADDING
            );
        }
        
        // Bottom door
        if (this.doors.bottom) {
            ctx.fillStyle = doorColor;
            ctx.fillRect(
                CONFIG.CANVAS_WIDTH / 2 - doorWidth / 2,
                CONFIG.CANVAS_HEIGHT - CONFIG.ROOM_PADDING,
                doorWidth,
                CONFIG.ROOM_PADDING
            );
        }
        
        // Left door
        if (this.doors.left) {
            ctx.fillStyle = doorColor;
            ctx.fillRect(
                0,
                CONFIG.CANVAS_HEIGHT / 2 - doorHeight / 2,
                CONFIG.ROOM_PADDING,
                doorHeight
            );
        }
        
        // Right door
        if (this.doors.right) {
            ctx.fillStyle = doorColor;
            ctx.fillRect(
                CONFIG.CANVAS_WIDTH - CONFIG.ROOM_PADDING,
                CONFIG.CANVAS_HEIGHT / 2 - doorHeight / 2,
                CONFIG.ROOM_PADDING,
                doorHeight
            );
        }
    }
    
    getBounds() {
        return {
            left: CONFIG.ROOM_PADDING,
            right: CONFIG.CANVAS_WIDTH - CONFIG.ROOM_PADDING,
            top: CONFIG.ROOM_PADDING,
            bottom: CONFIG.CANVAS_HEIGHT - CONFIG.ROOM_PADDING
        };
    }
    
    isCleared() {
        return this.cleared;
    }
    
    openDoors() {
        this.doorsOpened = true;
    }
    
    addPickup(pickup) {
        this.pickups.push(pickup);
    }
    
    setDoor(direction, value) {
        this.doors[direction] = value;
    }
}
