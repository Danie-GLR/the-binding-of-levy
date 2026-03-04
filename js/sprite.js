/**
 * Sprite and Animation System
 */

export class SpriteSheet {
    constructor(imagePath, frameWidth, frameHeight) {
        this.image = new Image();
        this.imagePath = imagePath;
        this.frameWidth = frameWidth;
        this.frameHeight = frameHeight;
        this.loaded = false;
        this.loadPromise = null;
        
        // Create a promise that resolves when image loads
        this.loadPromise = new Promise((resolve, reject) => {
            this.image.onload = () => {
                this.loaded = true;
                console.log(`✓ Loaded sprite sheet: ${imagePath}`);
                resolve();
            };
            
            this.image.onerror = (error) => {
                console.error(`✗ Failed to load sprite sheet: ${imagePath}`, error);
                reject(error);
            };
        });
        
        this.image.src = imagePath;
    }
    
    drawFrame(ctx, frameX, frameY, x, y, width, height) {
        if (!this.loaded) return;
        
        ctx.drawImage(
            this.image,
            frameX * this.frameWidth,
            frameY * this.frameHeight,
            this.frameWidth,
            this.frameHeight,
            x,
            y,
            width || this.frameWidth,
            height || this.frameHeight
        );
    }
}

export class Animation {
    constructor(spriteSheet, frames, frameRate = 10) {
        this.spriteSheet = spriteSheet;
        this.frames = frames; // Array of {x, y} frame coordinates
        this.frameRate = frameRate;
        this.currentFrame = 0;
        this.frameTimer = 0;
        this.loop = true;
        this.playing = true;
    }
    
    update(dt) {
        if (!this.playing) return;
        
        this.frameTimer += dt;
        if (this.frameTimer >= 1 / this.frameRate) {
            this.frameTimer = 0;
            this.currentFrame++;
            
            if (this.currentFrame >= this.frames.length) {
                if (this.loop) {
                    this.currentFrame = 0;
                } else {
                    this.currentFrame = this.frames.length - 1;
                    this.playing = false;
                }
            }
        }
    }
    
    getCurrentFrame() {
        return this.frames[this.currentFrame];
    }
    
    reset() {
        this.currentFrame = 0;
        this.frameTimer = 0;
        this.playing = true;
    }
    
    render(ctx, x, y, width, height) {
        const frame = this.getCurrentFrame();
        this.spriteSheet.drawFrame(ctx, frame.x, frame.y, x, y, width, height);
    }
}

export class AnimationManager {
    constructor() {
        this.animations = {};
        this.currentAnimation = null;
        this.previousAnimation = null;
    }
    
    addAnimation(name, animation) {
        this.animations[name] = animation;
        if (!this.currentAnimation) {
            this.currentAnimation = name;
        }
    }
    
    play(name, reset = false) {
        if (this.animations[name] && this.currentAnimation !== name) {
            this.previousAnimation = this.currentAnimation;
            this.currentAnimation = name;
            if (reset) {
                this.animations[name].reset();
            }
        }
    }
    
    update(dt) {
        if (this.currentAnimation && this.animations[this.currentAnimation]) {
            this.animations[this.currentAnimation].update(dt);
        }
    }
    
    render(ctx, x, y, width, height) {
        if (this.currentAnimation && this.animations[this.currentAnimation]) {
            this.animations[this.currentAnimation].render(ctx, x, y, width, height);
        }
    }
    
    getCurrentAnimation() {
        return this.animations[this.currentAnimation];
    }
}

// Sprite asset manager
export class AssetManager {
    constructor() {
        this.spriteSheets = {};
        this.loadingPromises = [];
    }// Use the sprite sheet's built-in load promise
        this.loadingPromises.push(spriteSheet.loadPiteSheet(path, frameWidth, frameHeight);
        this.spriteSheets[name] = spriteSheet;
        
        const promise = new Promise((resolve) => {
            spriteSheet.image.onload = () => resolve();
        });
        this.loadingPromises.push(promise);
        
        return spriteSheet;
    }
    
    getSpriteSheet(name) {
        return this.spriteSheets[name];
    }
    
    async waitForLoad() {
        await Promise.all(this.loadingPromises);
    }
}
