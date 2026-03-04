/**
 * Main entry point for The Binding of Levy
 */

import { Game } from './game.js';

// Global game instance
let game = null;

// Menu screens
const menuScreen = document.getElementById('menu-screen');
const gameScreen = document.getElementById('game-screen');
const pauseScreen = document.getElementById('pause-screen');
const gameOverScreen = document.getElementById('game-over-screen');
const canvas = document.getElementById('game-canvas');

// Menu buttons
const startBtn = document.getElementById('start-btn');
const controlsBtn = document.getElementById('controls-btn');
const aboutBtn = document.getElementById('about-btn');
const resumeBtn = document.getElementById('resume-btn');
const restartBtn = document.getElementById('restart-btn');
const quitBtn = document.getElementById('quit-btn');
const restartGameBtn = document.getElementById('restart-game-btn');
const menuBtn = document.getElementById('menu-btn');

// Info panels
const controlsInfo = document.getElementById('controls-info');
const aboutInfo = document.getElementById('about-info');
const backBtns = document.querySelectorAll('.back-btn');

// Initialize
function init() {
    // Menu button handlers
    startBtn.addEventListener('click', startGame);
    
    controlsBtn.addEventListener('click', () => {
        document.querySelector('.menu-options').style.display = 'none';
        controlsInfo.classList.remove('hidden');
    });
    
    aboutBtn.addEventListener('click', () => {
        document.querySelector('.menu-options').style.display = 'none';
        aboutInfo.classList.remove('hidden');
    });
    
    backBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            controlsInfo.classList.add('hidden');
            aboutInfo.classList.add('hidden');
            document.querySelector('.menu-options').style.display = 'flex';
        });
    });
    
    // Game control handlers
    resumeBtn.addEventListener('click', () => {
        if (game) game.resume();
    });
    
    restartBtn.addEventListener('click', () => {
        pauseScreen.classList.remove('active');
        if (game) {
            game.stop();
            game = null;
        }
        startGame();
    });
    
    quitBtn.addEventListener('click', () => {
        pauseScreen.classList.remove('active');
        if (game) {
            game.stop();
            game = null;
        }
        showMenu();
    });
    
    restartGameBtn.addEventListener('click', () => {
        gameOverScreen.classList.remove('active');
        if (game) {
            game.restart();
        } else {
            startGame();
        }
    });
    
    menuBtn.addEventListener('click', () => {
        gameOverScreen.classList.remove('active');
        if (game) {
            game.stop();
            game = null;
        }
        showMenu();
    });
}

function startGame() {
    menuScreen.classList.remove('active');
    gameScreen.classList.add('active');
    
    if (game) {
        game.stop();
    }
    
    game = new Game(canvas);
    game.start();
}

function showMenu() {
    gameScreen.classList.remove('active');
    pauseScreen.classList.remove('active');
    gameOverScreen.classList.remove('active');
    menuScreen.classList.add('active');
}

// Start application
document.addEventListener('DOMContentLoaded', init);
