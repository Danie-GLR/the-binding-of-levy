/**
 * Dungeon class - manages procedural generation of rooms and floor layout
 */

import { CONFIG } from './constants.js';
import { Room } from './room.js';

export class Dungeon {
    constructor(floor) {
        this.floor = floor;
        this.rooms = new Map(); // Key: "x,y", Value: Room
        this.currentRoomCoords = { x: 0, y: 0 };
        
        this.generate();
    }
    
    generate() {
        // Generate a procedural dungeon layout
        const roomCount = 8 + Math.floor(Math.random() * 5); // 8-12 rooms per floor
        
        // Start with spawn room at (0, 0)
        const startRoom = new Room(0, 0, CONFIG.ROOM_TYPES.START);
        this.rooms.set('0,0', startRoom);
        
        // Generate connected rooms using random walk
        let currentX = 0;
        let currentY = 0;
        const generatedCoords = new Set(['0,0']);
        
        for (let i = 1; i < roomCount; i++) {
            // Try to place room adjacent to existing room
            const directions = [
                { x: 0, y: -1, dir: 'top', opposite: 'bottom' },
                { x: 0, y: 1, dir: 'bottom', opposite: 'top' },
                { x: -1, y: 0, dir: 'left', opposite: 'right' },
                { x: 1, y: 0, dir: 'right', opposite: 'left' }
            ];
            
            // Shuffle directions
            directions.sort(() => Math.random() - 0.5);
            
            let placed = false;
            for (const dir of directions) {
                const newX = currentX + dir.x;
                const newY = currentY + dir.y;
                const key = `${newX},${newY}`;
                
                if (!generatedCoords.has(key)) {
                    // Determine room type
                    let roomType = CONFIG.ROOM_TYPES.NORMAL;
                    if (i === roomCount - 1) {
                        roomType = CONFIG.ROOM_TYPES.BOSS;
                    } else if (Math.random() < 0.2) {
                        roomType = CONFIG.ROOM_TYPES.TREASURE;
                    }
                    
                    const newRoom = new Room(newX, newY, roomType);
                    this.rooms.set(key, newRoom);
                    generatedCoords.add(key);
                    
                    // Connect rooms
                    const currentRoom = this.rooms.get(`${currentX},${currentY}`);
                    currentRoom.setDoor(dir.dir, true);
                    newRoom.setDoor(dir.opposite, true);
                    
                    currentX = newX;
                    currentY = newY;
                    placed = true;
                    break;
                }
            }
            
            // If couldn't place, pick a random existing room
            if (!placed) {
                const existingRooms = Array.from(generatedCoords);
                const randomRoom = existingRooms[Math.floor(Math.random() * existingRooms.length)];
                const [x, y] = randomRoom.split(',').map(Number);
                currentX = x;
                currentY = y;
                i--; // Try again
            }
        }
    }
    
    getCurrentRoom() {
        const key = `${this.currentRoomCoords.x},${this.currentRoomCoords.y}`;
        return this.rooms.get(key);
    }
    
    moveRoom(direction) {
        let newX = this.currentRoomCoords.x;
        let newY = this.currentRoomCoords.y;
        
        switch(direction) {
            case 'top':
                newY--;
                break;
            case 'bottom':
                newY++;
                break;
            case 'left':
                newX--;
                break;
            case 'right':
                newX++;
                break;
        }
        
        const key = `${newX},${newY}`;
        if (this.rooms.has(key)) {
            this.currentRoomCoords.x = newX;
            this.currentRoomCoords.y = newY;
            return this.rooms.get(key);
        }
        
        return null;
    }
    
    getRoomAt(x, y) {
        const key = `${x},${y}`;
        return this.rooms.get(key);
    }
    
    getAllRooms() {
        return Array.from(this.rooms.values());
    }
}
