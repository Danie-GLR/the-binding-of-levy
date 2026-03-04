/**
 * Input manager for handling keyboard input
 */

export class InputManager {
    constructor() {
        this.keys = {};
        this.keysPressed = {};
        
        window.addEventListener('keydown', (e) => {
            this.keys[e.code] = true;
            if (!this.keysPressed[e.code]) {
                this.keysPressed[e.code] = true;
            }
        });
        
        window.addEventListener('keyup', (e) => {
            this.keys[e.code] = false;
            this.keysPressed[e.code] = false;
        });
    }
    
    isKeyDown(keyCode) {
        return this.keys[keyCode] || false;
    }
    
    isKeyPressed(keyCode) {
        if (this.keysPressed[keyCode]) {
            this.keysPressed[keyCode] = false;
            return true;
        }
        return false;
    }
    
    reset() {
        this.keys = {};
        this.keysPressed = {};
    }
}
