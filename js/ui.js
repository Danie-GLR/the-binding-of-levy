/**
 * UI class - manages HUD and UI elements
 */

import { CONFIG } from './constants.js';

export class UI {
    constructor() {
        this.healthDisplay = document.getElementById('hearts-container');
        this.floorDisplay = document.getElementById('floor-display');
        this.roomDisplay = document.getElementById('room-display');
        this.bombsDisplay = document.getElementById('bombs-display');
        this.keysDisplay = document.getElementById('keys-display');
        this.coinsDisplay = document.getElementById('coins-display');
    }
    
    updateHealth(currentHealth, maxHealth) {
        // Clear existing hearts
        this.healthDisplay.innerHTML = '';
        
        const maxHearts = Math.ceil(maxHealth / 2);
        const fullHearts = Math.floor(currentHealth / 2);
        const hasHalfHeart = currentHealth % 2 === 1;
        
        // Add full hearts
        for (let i = 0; i < fullHearts; i++) {
            const heart = document.createElement('span');
            heart.className = 'heart full';
            this.healthDisplay.appendChild(heart);
        }
        
        // Add half heart if needed
        if (hasHalfHeart) {
            const heart = document.createElement('span');
            heart.className = 'heart half';
            this.healthDisplay.appendChild(heart);
        }
        
        // Add empty hearts
        const emptyHearts = maxHearts - fullHearts - (hasHalfHeart ? 1 : 0);
        for (let i = 0; i < emptyHearts; i++) {
            const heart = document.createElement('span');
            heart.className = 'heart empty';
            this.healthDisplay.appendChild(heart);
        }
    }
    
    updateFloor(floor) {
        this.floorDisplay.textContent = floor;
    }
    
    updateRoomType(roomType) {
        const typeNames = {
            'start': 'Start',
            'normal': 'Normal',
            'boss': 'BOSS',
            'treasure': 'Treasure',
            'shop': 'Shop',
            'secret': 'Secret',
            'devil': 'Devil',
            'angel': 'Angel'
        };
        this.roomDisplay.textContent = typeNames[roomType] || roomType;
        
        // Color code based on room type
        if (roomType === 'boss') {
            this.roomDisplay.style.color = '#9c27b0';
            this.roomDisplay.style.fontWeight = 'bold';
        } else if (roomType === 'treasure') {
            this.roomDisplay.style.color = '#4caf50';
        } else if (roomType === 'devil') {
            this.roomDisplay.style.color = '#f44336';
        } else if (roomType === 'angel') {
            this.roomDisplay.style.color = '#40c4ff';
        } else {
            this.roomDisplay.style.color = '#fff';
            this.roomDisplay.style.fontWeight = 'normal';
        }
    }
    
    updateInventory(bombs, keys, coins) {
        this.bombsDisplay.textContent = bombs;
        this.keysDisplay.textContent = keys;
        this.coinsDisplay.textContent = coins;
    }
    
    showMessage(message, duration = 2000) {
        // TODO: Implement message display
        console.log(message);
    }
}
