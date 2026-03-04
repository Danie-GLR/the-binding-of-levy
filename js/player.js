/**
 * Player class
 */

import { CONFIG, KEYS } from './constants.js';
import { Tear } from './projectile.js';
import { Animation, AnimationManager } from './sprite.js';

export class Player {
    constructor(x, y, input, spriteSheet) {
        this.x = x;
        this.y = y;
        this.width = CONFIG.PLAYER_SIZE;
        this.height = CONFIG.PLAYER_SIZE;
        this.input = input;
        this.spriteSheet = spriteSheet;
        
        // Stats
        this.health = CONFIG.PLAYER_MAX_HEALTH;
        this.maxHealth = CONFIG.PLAYER_MAX_HEALTH;
        this.speed = CONFIG.PLAYER_SPEED;
        this.damage = CONFIG.PLAYER_DAMAGE;
        this.tearSpeed = CONFIG.PLAYER_TEAR_SPEED;
        this.tearRange = CONFIG.PLAYER_TEAR_RANGE;
        this.fireRate = CONFIG.PLAYER_FIRE_RATE;
        
        // Shooting
        this.tears = [];
        this.lastShootTime = 0;
        
        // Inventory
        this.coins = 0;
        this.bombs = 3;
        this.keys = 1;
        
        // Items
        this.activeItem = null;
        this.passiveItems = [];
        this.trinket = null;
        
        // State
        this.invincible = false;
        this.invincibleTimer = 0;
        this.invincibleDuration = 1000; // 1 second
        
        // Velocity
        this.vx = 0;
        this.vy = 0;
        
        // Animation
        this.animationManager = new AnimationManager();
        this.direction = 'down';
        this.moving = false;
        this.setupAnimations();
    }
    
    setupAnimations() {
        if (!this.spriteSheet) {
            console.warn('⚠️ No sprite sheet provided to player');
            return;
        }
        
        console.log('🎬 Setting up player animations...');
        
        // Head idle animation (row 0, frames 0-9)
        const headIdleFrames = [];
        for (let i = 0; i < 10; i++) {
            headIdleFrames.push({ x: i, y: 0 });
        }
        this.animationManager.addAnimation('idle', new Animation(this.spriteSheet, headIdleFrames, 8));
        
        // Walk down animation (row 2, frames 0-9)
        const walkDownFrames = [];
        for (let i = 0; i < 10; i++) {
            walkDownFrames.push({ x: i, y: 2 });
        }
        this.animationManager.addAnimation('walk_down', new Animation(this.spriteSheet, walkDownFrames, 12));
        
        // Walk left animation (row 3, frames 0-9)
        const walkLeftFrames = [];
        for (let i = 0; i < 10; i++) {
            walkLeftFrames.push({ x: i, y: 3 });
        }
        this.animationManager.addAnimation('walk_left', new Animation(this.spriteSheet, walkLeftFrames, 12));
        
        // Walk right animation (row 4, frames 0-9)
        const walkRightFrames = [];
        for (let i = 0; i < 10; i++) {
            walkRightFrames.push({ x: i, y: 4 });
        }
        this.animationManager.addAnimation('walk_right', new Animation(this.spriteSheet, walkRightFrames, 12));
        
        // Walk up animation (row 1, frames 0-9)
        const walkUpFrames = [];
        for (let i = 0; i < 10; i++) {
            walkUpFrames.push({ x: i, y: 1 });
        }
        this.animationManager.addAnimation('walk_up', new Animation(this.spriteSheet, walkUpFrames, 12));
    }
    
    update(dt, room) {
        // Handle movement
        this.handleMovement();
        
        // Update animation based on movement
        this.updateAnimation();
        
        // Update animation manager
        this.animationManager.update(dt);
        
        // Apply velocity with room bounds
        const bounds = room.getBounds();
        this.x += this.vx;
        this.y += this.vy;
        
        // Constrain to room bounds
        if (this.x < bounds.left) this.x = bounds.left;
        if (this.x + this.width > bounds.right) this.x = bounds.right - this.width;
        if (this.y < bounds.top) this.y = bounds.top;
        if (this.y + this.height > bounds.bottom) this.y = bounds.bottom - this.height;
        
        // Handle shooting
        this.handleShooting();
        
        // Update tears
        this.tears = this.tears.filter(tear => !tear.destroyed);
        this.tears.forEach(tear => tear.update(dt));
        
        // Update invincibility
        if (this.invincible) {
            this.invincibleTimer -= dt * 1000;
            if (this.invincibleTimer <= 0) {
                this.invincible = false;
            }
        }
    }
    
    handleMovement() {
        this.vx = 0;
        this.vy = 0;
        this.moving = false;
        
        if (this.input.isKeyDown(KEYS.W)) {
            this.vy -= this.speed;
            this.direction = 'up';
            this.moving = true;
        }
        if (this.input.isKeyDown(KEYS.S)) {
            this.vy += this.speed;
            this.direction = 'down';
            this.moving = true;
        }
        if (this.input.isKeyDown(KEYS.A)) {
            this.vx -= this.speed;
            this.direction = 'left';
            this.moving = true;
        }
        if (this.input.isKeyDown(KEYS.D)) {
            this.vx += this.speed;
            this.direction = 'right';
            this.moving = true;
        }
        
        // Normalize diagonal movement
        if (this.vx !== 0 && this.vy !== 0) {
            const length = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
            this.vx = (this.vx / length) * this.speed;
            this.vy = (this.vy / length) * this.speed;
        }
    }
    
    updateAnimation() {
        // Determine which animation to play
        if (this.moving) {
            // Play walk animation based on direction
            if (this.direction === 'up') {
                this.animationManager.play('walk_up');
            } else if (this.direction === 'down') {
                this.animationManager.play('walk_down');
            } else if (this.direction === 'left') {
                this.animationManager.play('walk_left');
            } else if (this.direction === 'right') {
                this.animationManager.play('walk_right');
            }
        } else {
            // Play idle animation
            this.animationManager.play('idle');
        }
    }
    
    handleShooting() {
        const now = Date.now();
        if (now - this.lastShootTime < this.fireRate) return;
        
        let shootDir = null;
        
        // Check for 8-directional shooting
        const up = this.input.isKeyDown(KEYS.ARROW_UP);
        const down = this.input.isKeyDown(KEYS.ARROW_DOWN);
        const left = this.input.isKeyDown(KEYS.ARROW_LEFT);
        const right = this.input.isKeyDown(KEYS.ARROW_RIGHT);
        
        if (up && !down && !left && !right) shootDir = { x: 0, y: -1 };
        else if (down && !up && !left && !right) shootDir = { x: 0, y: 1 };
        else if (left && !right && !up && !down) shootDir = { x: -1, y: 0 };
        else if (right && !left && !up && !down) shootDir = { x: 1, y: 0 };
        else if (up && left) shootDir = { x: -0.707, y: -0.707 };
        else if (up && right) shootDir = { x: 0.707, y: -0.707 };
        else if (down && left) shootDir = { x: -0.707, y: 0.707 };
        else if (down && right) shootDir = { x: 0.707, y: 0.707 };
        
        if (shootDir) {
            this.shoot(shootDir);
            this.lastShootTime = now;
        }
    }
    
    shoot(direction) {
        const tear = new Tear(
            this.x + this.width / 2,
            this.y + this.height / 2,
            direction,
            this.tearSpeed,
            this.damage,
            this.tearRange
        );
        this.tears.push(tear);
    }
    
    takeDamage(amount) {
        if (this.invincible) return;
        
        this.health -= amount;
        if (this.health < 0) this.health = 0;
        
        this.invincible = true;
        this.invincibleTimer = this.invincibleDuration;
    }
    
    heal(amount) {
        this.health = Math.min(this.health + amount, this.maxHealth);
    }
    
    collect(pickup) {
        switch(pickup.type) {
            case CONFIG.PICKUP_TYPES.COIN:
                this.coins++;
                break;
            case CONFIG.PICKUP_TYPES.BOMB:
                this.bombs++;
                break;
            case CONFIG.PICKUP_TYPES.KEY:
                this.keys++;
                break;
            case CONFIG.PICKUP_TYPES.HEART:
                this.heal(2);
                break;
            case CONFIG.PICKUP_TYPES.SOUL_HEART:
                this.maxHealth += 2;
                this.health += 2;
                break;
        }
    }
    
    render(ctx) {
        // Draw player (flashing when invincible)
        if (!this.invincible || Math.floor(this.invincibleTimer / 100) % 2 === 0) {
            if (this.spriteSheet && this.spriteSheet.loaded) {
                // Render sprite animation (slightly larger than hitbox for visual appeal)
                this.animationManager.render(ctx, this.x - 8, this.y - 8, this.width + 16, this.height + 16);
            } else {
                // Fallback to simple rectangle if sprites not loaded
                ctx.fillStyle = CONFIG.COLORS.PLAYER;
                ctx.fillRect(this.x, this.y, this.width, this.height);
                
                // Draw face
                ctx.fillStyle = '#000';
                ctx.fillRect(this.x + 8, this.y + 8, 4, 4);
                ctx.fillRect(this.x + 20, this.y + 8, 4, 4);
                ctx.fillRect(this.x + 10, this.y + 20, 12, 3);
            }
        }
        
        // Render tears
        this.tears.forEach(tear => tear.render(ctx));
    }
}
