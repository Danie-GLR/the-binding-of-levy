/**
 * Pickup items (coins, bombs, keys, hearts)
 */

import { CONFIG } from './constants.js';

export class Pickup {
    constructor(x, y, type) {
        this.x = x;
        this.y = y;
        this.width = 16;
        this.height = 16;
        this.type = type;
        this.destroyed = false;
        
        // Floating animation
        this.floatOffset = 0;
        this.floatSpeed = 2;
    }
    
    update(dt) {
        this.floatOffset += this.floatSpeed * dt;
    }
    
    render(ctx) {
        const yOffset = Math.sin(this.floatOffset) * 3;
        
        ctx.save();
        ctx.translate(0, yOffset);
        
        switch(this.type) {
            case CONFIG.PICKUP_TYPES.COIN:
                ctx.fillStyle = CONFIG.COLORS.COIN;
                ctx.beginPath();
                ctx.arc(this.x + this.width / 2, this.y + this.height / 2, this.width / 2, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#ff8f00';
                ctx.beginPath();
                ctx.arc(this.x + this.width / 2, this.y + this.height / 2, this.width / 3, 0, Math.PI * 2);
                ctx.fill();
                break;
                
            case CONFIG.PICKUP_TYPES.BOMB:
                ctx.fillStyle = CONFIG.COLORS.BOMB;
                ctx.beginPath();
                ctx.arc(this.x + this.width / 2, this.y + this.height / 2, this.width / 2, 0, Math.PI * 2);
                ctx.fill();
                ctx.fillStyle = '#ff0000';
                ctx.fillRect(this.x + this.width / 2 - 1, this.y - 4, 2, 8);
                break;
                
            case CONFIG.PICKUP_TYPES.KEY:
                ctx.fillStyle = CONFIG.COLORS.KEY;
                ctx.fillRect(this.x + 2, this.y + 4, 8, 8);
                ctx.fillRect(this.x + 10, this.y + 6, 4, 4);
                ctx.fillRect(this.x + 10, this.y + 2, 2, 2);
                ctx.fillRect(this.x + 10, this.y + 10, 2, 2);
                break;
                
            case CONFIG.PICKUP_TYPES.HEART:
                ctx.fillStyle = CONFIG.COLORS.HEART;
                ctx.beginPath();
                ctx.moveTo(this.x + this.width / 2, this.y + this.height);
                ctx.lineTo(this.x, this.y + this.height / 3);
                ctx.lineTo(this.x, this.y);
                ctx.lineTo(this.x + this.width / 2, this.y + this.height / 3);
                ctx.lineTo(this.x + this.width, this.y);
                ctx.lineTo(this.x + this.width, this.y + this.height / 3);
                ctx.closePath();
                ctx.fill();
                break;
                
            case CONFIG.PICKUP_TYPES.SOUL_HEART:
                ctx.fillStyle = '#40c4ff';
                ctx.beginPath();
                ctx.moveTo(this.x + this.width / 2, this.y + this.height);
                ctx.lineTo(this.x, this.y + this.height / 3);
                ctx.lineTo(this.x, this.y);
                ctx.lineTo(this.x + this.width / 2, this.y + this.height / 3);
                ctx.lineTo(this.x + this.width, this.y);
                ctx.lineTo(this.x + this.width, this.y + this.height / 3);
                ctx.closePath();
                ctx.fill();
                break;
        }
        
        ctx.restore();
    }
    
    destroy() {
        this.destroyed = true;
    }
}
