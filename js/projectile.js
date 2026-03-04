/**
 * Projectile classes (Tears and Enemy projectiles)
 */

import { CONFIG } from './constants.js';

export class Tear {
    constructor(x, y, direction, speed, damage, range) {
        this.x = x;
        this.y = y;
        this.width = CONFIG.TEAR_SIZE;
        this.height = CONFIG.TEAR_SIZE;
        this.direction = direction;
        this.speed = speed;
        this.damage = damage;
        this.maxRange = range;
        this.distanceTraveled = 0;
        this.destroyed = false;
    }
    
    update(dt) {
        const moveX = this.direction.x * this.speed;
        const moveY = this.direction.y * this.speed;
        
        this.x += moveX;
        this.y += moveY;
        
        this.distanceTraveled += Math.sqrt(moveX * moveX + moveY * moveY);
        
        // Check if out of range
        if (this.distanceTraveled >= this.maxRange) {
            this.destroyed = true;
        }
        
        // Check if out of bounds
        if (this.x < 0 || this.x > CONFIG.CANVAS_WIDTH ||
            this.y < 0 || this.y > CONFIG.CANVAS_HEIGHT) {
            this.destroyed = true;
        }
    }
    
    render(ctx) {
        ctx.fillStyle = CONFIG.COLORS.TEAR;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.width / 2, 0, Math.PI * 2);
        ctx.fill();
    }
    
    destroy() {
        this.destroyed = true;
    }
}

export class EnemyProjectile {
    constructor(x, y, direction, speed, damage) {
        this.x = x;
        this.y = y;
        this.width = CONFIG.TEAR_SIZE;
        this.height = CONFIG.TEAR_SIZE;
        this.direction = direction;
        this.speed = speed;
        this.damage = damage;
        this.destroyed = false;
    }
    
    update(dt) {
        this.x += this.direction.x * this.speed;
        this.y += this.direction.y * this.speed;
        
        // Check if out of bounds
        if (this.x < 0 || this.x > CONFIG.CANVAS_WIDTH ||
            this.y < 0 || this.y > CONFIG.CANVAS_HEIGHT) {
            this.destroyed = true;
        }
    }
    
    render(ctx) {
        ctx.fillStyle = CONFIG.COLORS.ENEMY_PROJECTILE;
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.width / 2, 0, Math.PI * 2);
        ctx.fill();
    }
    
    destroy() {
        this.destroyed = true;
    }
}
