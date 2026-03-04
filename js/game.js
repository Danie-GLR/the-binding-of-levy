/**
 * Main game class - handles game loop and state management
 */

import { CONFIG } from './constants.js';
import { InputManager } from './input.js';
import { Player } from './player.js';
import { Dungeon } from './dungeon.js';
import { UI } from './ui.js';
import { AssetManager } from './sprite.js';

export class Game {
    constructor(canvas) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.canvas.width = CONFIG.CANVAS_WIDTH;
        this.canvas.height = CONFIG.CANVAS_HEIGHT;
        
        this.input = new InputManager();
        this.ui = new UI();
        
        this.state = 'loading'; // loading, playing, paused, gameover
        this.floor = 1;
        this.enemiesKilled = 0;
        
        this.lastTime = 0;
        this.animationId = null;
        
        // Asset management
        this.assetManager = new AssetManager();
        this.loadAssets().then(() => {
            this.init();
            this.state = 'playing';
        });
    }
    
    async loadAssets() {
        console.log('🎨 Starting asset loading...');
        
        // Load Isaac sprite sheet (32x32 frames)
        this.isaacSpriteSheet = this.assetManager.loadSpriteSheet(
            'isaac',
            'assets/isaac-sprite.png',
            32,
            32
        );
        
        console.log('⏳ Waiting for assets to load...');
        await this.assetManager.waitForLoad();
        console.log('✓ All assets loaded!');
    }
    
    init() {
        // Create player at center of room
        this.player = new Player(
            CONFIG.CANVAS_WIDTH / 2,
            CONFIG.CANVAS_HEIGHT / 2,
            this.input,
            this.isaacSpriteSheet
        );
        
        // Create dungeon
        this.dungeon = new Dungeon(this.floor);
        this.currentRoom = this.dungeon.getCurrentRoom();
        
        // Update UI
        this.ui.updateFloor(this.floor);
        this.ui.updateRoomType(this.currentRoom.type);
    }
    
    start() {
        this.lastTime = performance.now();
        this.loop();
    }
    
    loop = (currentTime = 0) => {
        const deltaTime = (currentTime - this.lastTime) / 1000;
        this.lastTime = currentTime;
        
        this.update(deltaTime);
        this.render();
        
        this.animationId = requestAnimationFrame(this.loop);
    }
    
    update(dt) {
        if (this.state === 'loading') return;
        if (this.state !== 'playing') return;
        
        // Handle pause
        if (this.input.isKeyPressed('Escape')) {
            this.pause();
            return;
        }
        
        // Update player
        this.player.update(dt, this.currentRoom);
        
        // Update current room (enemies, projectiles, etc.)
        this.currentRoom.update(dt, this.player);
        
        // Check collisions
        this.checkCollisions();
        
        // Check room transition
        this.checkRoomTransition();
        
        // Update UI
        this.ui.updateHealth(this.player.health, this.player.maxHealth);
        this.ui.updateInventory(this.player.bombs, this.player.keys, this.player.coins);
        
        // Check for room completion
        if (this.currentRoom.isCleared() && !this.currentRoom.doorsOpened) {
            this.currentRoom.openDoors();
        }
        
        // Check game over
        if (this.player.health <= 0) {
            this.gameOver();
        }
    }
    
    checkCollisions() {
        // Player tears vs enemies
        for (const tear of this.player.tears) {
            for (const enemy of this.currentRoom.enemies) {
                if (this.collides(tear, enemy)) {
                    enemy.takeDamage(tear.damage);
                    tear.destroy();
                    
                    if (enemy.health <= 0) {
                        this.enemiesKilled++;
                        enemy.dropLoot(this.currentRoom);
                    }
                }
            }
        }
        
        // Enemy collisions with player
        for (const enemy of this.currentRoom.enemies) {
            if (this.collides(this.player, enemy) && !this.player.invincible) {
                this.player.takeDamage(CONFIG.ENEMY_DAMAGE);
            }
        }
        
        // Player pickup collection
        for (const pickup of this.currentRoom.pickups) {
            if (this.collides(this.player, pickup)) {
                this.player.collect(pickup);
                pickup.destroy();
            }
        }
    }
    
    collides(obj1, obj2) {
        return obj1.x < obj2.x + obj2.width &&
               obj1.x + obj1.width > obj2.x &&
               obj1.y < obj2.y + obj2.height &&
               obj1.y + obj1.height > obj2.y;
    }
    
    checkRoomTransition() {
        const bounds = this.currentRoom.getBounds();
        
        // Check if player is at a door
        if (this.player.x < bounds.left && this.currentRoom.doors.left) {
            this.transitionRoom('left');
        } else if (this.player.x + this.player.width > bounds.right && this.currentRoom.doors.right) {
            this.transitionRoom('right');
        } else if (this.player.y < bounds.top && this.currentRoom.doors.top) {
            this.transitionRoom('top');
        } else if (this.player.y + this.player.height > bounds.bottom && this.currentRoom.doors.bottom) {
            this.transitionRoom('bottom');
        }
    }
    
    transitionRoom(direction) {
        const newRoom = this.dungeon.moveRoom(direction);
        if (newRoom) {
            this.currentRoom = newRoom;
            
            // Reposition player at opposite door
            if (direction === 'left') {
                this.player.x = CONFIG.CANVAS_WIDTH - CONFIG.ROOM_PADDING - 50;
            } else if (direction === 'right') {
                this.player.x = CONFIG.ROOM_PADDING + 50;
            } else if (direction === 'top') {
                this.player.y = CONFIG.CANVAS_HEIGHT - CONFIG.ROOM_PADDING - 50;
            } else if (direction === 'bottom') {
                this.player.y = CONFIG.ROOM_PADDING + 50;
            }
            
            this.ui.updateRoomType(this.currentRoom.type);
        }
    }
    
    render() {
        // Clear canvas
        this.ctx.fillStyle = CONFIG.COLORS.BACKGROUND;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Show loading screen
        if (this.state === 'loading') {
            this.ctx.fillStyle = '#fff';
            this.ctx.font = '24px Courier New';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('Loading Assets...', this.canvas.width / 2, this.canvas.height / 2);
            return;
        }
        
        // Render current room
        this.currentRoom.render(this.ctx);
        
        // Render player
        this.player.render(this.ctx);
    }
    
    pause() {
        this.state = 'paused';
        document.getElementById('pause-screen').classList.add('active');
    }
    
    resume() {
        this.state = 'playing';
        document.getElementById('pause-screen').classList.remove('active');
        this.lastTime = performance.now();
    }
    
    gameOver() {
        this.state = 'gameover';
        document.getElementById('floors-survived').textContent = this.floor;
        document.getElementById('enemies-killed').textContent = this.enemiesKilled;
        document.getElementById('game-over-screen').classList.add('active');
    }
    
    restart() {
        this.floor = 1;
        this.enemiesKilled = 0;
        this.state = 'playing';
        this.init();
        document.getElementById('game-over-screen').classList.remove('active');
        this.lastTime = performance.now();
    }
    
    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }
}
