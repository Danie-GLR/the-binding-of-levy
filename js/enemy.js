/**
 * Enemy classes
 */

import { CONFIG } from './constants.js';
import { Pickup } from './pickup.js';

export class Enemy {
    constructor(x, y) {
        this.x = x;
        this.y = y;
        this.width = CONFIG.ENEMY_SIZE;
        this.height = CONFIG.ENEMY_SIZE;
        
        this.health = CONFIG.ENEMY_HEALTH;
        this.maxHealth = CONFIG.ENEMY_HEALTH;
        this.speed = CONFIG.ENEMY_SPEED;
        this.damage = CONFIG.ENEMY_DAMAGE;
        
        this.destroyed = false;
        this.vx = 0;
        this.vy = 0;
    }
    
    update(dt, player) {
        // Basic AI: Chase player
        const dx = player.x + player.width / 2 - (this.x + this.width / 2);
        const dy = player.y + player.height / 2 - (this.y + this.height / 2);
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < CONFIG.ENEMY_CHASE_RANGE && distance > CONFIG.ENEMY_ATTACK_RANGE) {
            this.vx = (dx / distance) * this.speed;
            this.vy = (dy / distance) * this.speed;
        } else {
            this.vx *= 0.9;
            this.vy *= 0.9;
        }
        
        this.x += this.vx;
        this.y += this.vy;
    }
    
    takeDamage(amount) {
        this.health -= amount;
        if (this.health <= 0) {
            this.destroyed = true;
        }
    }
    
    dropLoot(room) {
        // Random chance to drop items
        const rand = Math.random();
        if (rand < 0.3) {
            // 30% chance for coin
            room.addPickup(new Pickup(this.x, this.y, CONFIG.PICKUP_TYPES.COIN));
        } else if (rand < 0.4) {
            // 10% chance for bomb
            room.addPickup(new Pickup(this.x, this.y, CONFIG.PICKUP_TYPES.BOMB));
        } else if (rand < 0.45) {
            // 5% chance for key
            room.addPickup(new Pickup(this.x, this.y, CONFIG.PICKUP_TYPES.KEY));
        } else if (rand < 0.55) {
            // 10% chance for heart
            room.addPickup(new Pickup(this.x, this.y, CONFIG.PICKUP_TYPES.HEART));
        }
    }
    
    render(ctx) {
        // Health bar
        const healthPercent = this.health / this.maxHealth;
        ctx.fillStyle = '#000';
        ctx.fillRect(this.x, this.y - 10, this.width, 4);
        ctx.fillStyle = '#0f0';
        ctx.fillRect(this.x, this.y - 10, this.width * healthPercent, 4);
        
        // Body
        ctx.fillStyle = CONFIG.COLORS.ENEMY;
        ctx.fillRect(this.x, this.y, this.width, this.height);
        
        // Eyes
        ctx.fillStyle = '#000';
        ctx.fillRect(this.x + 8, this.y + 10, 4, 4);
        ctx.fillRect(this.x + 20, this.y + 10, 4, 4);
    }
}

export class FlyEnemy extends Enemy {
    constructor(x, y) {
        super(x, y);
        this.speed = CONFIG.ENEMY_SPEED * 1.5;
        this.health = CONFIG.ENEMY_HEALTH * 0.5;
        this.maxHealth = this.health;
        this.width = 24;
        this.height = 24;
    }
    
    render(ctx) {
        // Health bar
        const healthPercent = this.health / this.maxHealth;
        ctx.fillStyle = '#000';
        ctx.fillRect(this.x, this.y - 10, this.width, 4);
        ctx.fillStyle = '#0f0';
        ctx.fillRect(this.x, this.y - 10, this.width * healthPercent, 4);
        
        // Body (flying enemy - smaller and darker)
        ctx.fillStyle = '#c62828';
        ctx.beginPath();
        ctx.arc(this.x + this.width / 2, this.y + this.height / 2, this.width / 2, 0, Math.PI * 2);
        ctx.fill();
        
        // Wings
        ctx.fillStyle = '#b71c1c';
        ctx.fillRect(this.x - 4, this.y + 8, 4, 8);
        ctx.fillRect(this.x + this.width, this.y + 8, 4, 8);
    }
}

export class Boss extends Enemy {
    constructor(x, y) {
        super(x, y);
        this.width = CONFIG.BOSS_SIZE;
        this.height = CONFIG.BOSS_SIZE;
        this.health = CONFIG.BOSS_HEALTH;
        this.maxHealth = CONFIG.BOSS_HEALTH;
        this.speed = CONFIG.BOSS_SPEED;
        this.damage = CONFIG.BOSS_DAMAGE;
        
        this.attackTimer = 0;
        this.attackCooldown = 2000; // 2 seconds
        this.phase = 1;
    }
    
    update(dt, player) {
        super.update(dt, player);
        
        // Boss attack patterns
        this.attackTimer += dt * 1000;
        
        if (this.attackTimer >= this.attackCooldown) {
            this.attack(player);
            this.attackTimer = 0;
        }
        
        // Phase transitions
        if (this.health < this.maxHealth * 0.5 && this.phase === 1) {
            this.phase = 2;
            this.speed *= 1.5;
            this.attackCooldown *= 0.7;
        }
    }
    
    attack(player) {
        // Boss attack logic - could shoot projectiles, summon enemies, etc.
        // For now, just a placeholder
    }
    
    render(ctx) {
        // Health bar
        const healthPercent = this.health / this.maxHealth;
        ctx.fillStyle = '#000';
        ctx.fillRect(this.x, this.y - 20, this.width, 8);
        ctx.fillStyle = '#0f0';
        ctx.fillRect(this.x, this.y - 20, this.width * healthPercent, 8);
        
        // Boss name
        ctx.fillStyle = '#fff';
        ctx.font = '16px Courier New';
        ctx.textAlign = 'center';
        ctx.fillText('BOSS', this.x + this.width / 2, this.y - 25);
        
        // Body
        ctx.fillStyle = CONFIG.COLORS.BOSS;
        ctx.fillRect(this.x, this.y, this.width, this.height);
        
        // Eyes (bigger and more menacing)
        ctx.fillStyle = '#ff0000';
        ctx.fillRect(this.x + 12, this.y + 16, 12, 12);
        ctx.fillRect(this.x + 40, this.y + 16, 12, 12);
        
        // Mouth
        ctx.fillStyle = '#000';
        ctx.fillRect(this.x + 16, this.y + 44, 32, 8);
    }
}
