// Three.js background animation
let scene, camera, renderer, particles;
let mouseX = 0, mouseY = 0;
let targetX = 0, targetY = 0;
let windowHalfX = window.innerWidth / 2;
let windowHalfY = window.innerHeight / 2;
let style = 'particles'; // Default style
let raycaster = new THREE.Raycaster();
let mouse = new THREE.Vector2();
let explosionParticles = [];

const styles = {
    particles: {
        count: 5000,
        size: 2,
        color: 0x8B5CF6,
        spread: 2000,
        speed: 0.0001  // Slowed down
    },
    stars: {
        count: 2000,
        size: 1.5,
        color: 0xFFFFFF,
        spread: 1000,
        speed: 0.00005  // Slowed down
    },
    nebula: {
        count: 4000,
        size: 2.5,
        color: 0xEC4899,
        spread: 1800,
        speed: 0.0001  // Slowed down
    }
};

function init() {
    // Create scene
    scene = new THREE.Scene();
    
    // Create camera
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;
    
    // Create renderer
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(0x000000, 0);
    document.getElementById('background-container').appendChild(renderer.domElement);
    
    createParticles(style);
    
    // Add event listeners
    document.addEventListener('mousemove', onDocumentMouseMove, false);
    document.addEventListener('touchstart', onDocumentTouchStart, false);
    document.addEventListener('touchmove', onDocumentTouchMove, false);
    document.addEventListener('click', onDocumentClick, false);
    window.addEventListener('resize', onWindowResize, false);
    
    // Add style switcher
    createStyleSwitcher();
    
    // Start animation
    animate();
}

function createExplosion(position, color) {
    const particleCount = 50;
    const geometry = new THREE.BufferGeometry();
    const vertices = [];
    const velocities = [];
    
    for (let i = 0; i < particleCount; i++) {
        // Start all particles at the click position
        vertices.push(position.x, position.y, position.z);
        
        // Random velocity for each particle
        velocities.push(
            (Math.random() - 0.5) * 0.2,
            (Math.random() - 0.5) * 0.2,
            (Math.random() - 0.5) * 0.2
        );
    }
    
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    
    const material = new THREE.PointsMaterial({
        color: color,
        size: 2,
        transparent: true,
        opacity: 1,
        blending: THREE.AdditiveBlending
    });
    
    const explosion = new THREE.Points(geometry, material);
    explosion.userData.velocities = velocities;
    explosion.userData.life = 1.0; // Life starts at 1 and decreases to 0
    scene.add(explosion);
    explosionParticles.push(explosion);
}

function updateExplosions() {
    for (let i = explosionParticles.length - 1; i >= 0; i--) {
        const explosion = explosionParticles[i];
        const positions = explosion.geometry.attributes.position.array;
        const velocities = explosion.userData.velocities;
        
        // Update positions
        for (let j = 0; j < positions.length; j += 3) {
            positions[j] += velocities[j/3];
            positions[j + 1] += velocities[j/3 + 1];
            positions[j + 2] += velocities[j/3 + 2];
        }
        
        explosion.geometry.attributes.position.needsUpdate = true;
        
        // Decrease life
        explosion.userData.life -= 0.02;
        explosion.material.opacity = explosion.userData.life;
        
        // Remove dead explosions
        if (explosion.userData.life <= 0) {
            scene.remove(explosion);
            explosionParticles.splice(i, 1);
        }
    }
}

function onDocumentClick(event) {
    // Calculate mouse position in normalized device coordinates
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    
    // Update the picking ray with the camera and mouse position
    raycaster.setFromCamera(mouse, camera);
    
    // Calculate objects intersecting the picking ray
    const intersects = raycaster.intersectObject(particles);
    
    if (intersects.length > 0) {
        const intersect = intersects[0];
        const position = intersect.point;
        const color = styles[style].color;
        createExplosion(position, color);
    }
}

function createParticles(styleName) {
    // Remove existing particles if any
    if (particles) {
        scene.remove(particles);
    }
    
    const style = styles[styleName];
    const geometry = new THREE.BufferGeometry();
    const vertices = [];
    
    for (let i = 0; i < style.count; i++) {
        const x = THREE.MathUtils.randFloatSpread(style.spread);
        const y = THREE.MathUtils.randFloatSpread(style.spread);
        const z = THREE.MathUtils.randFloatSpread(style.spread);
        
        vertices.push(x, y, z);
    }
    
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    
    const material = new THREE.PointsMaterial({
        color: style.color,
        size: style.size,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending
    });
    
    particles = new THREE.Points(geometry, material);
    scene.add(particles);
}

function createStyleSwitcher() {
    const switcher = document.createElement('div');
    switcher.className = 'style-switcher';
    switcher.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        background: rgba(17, 17, 17, 0.7);
        backdrop-filter: blur(10px);
        padding: 10px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        display: flex;
        gap: 8px;
        transform-style: preserve-3d;
        transform: translateZ(0);
    `;
    
    Object.keys(styles).forEach(styleName => {
        const button = document.createElement('button');
        button.textContent = styleName.charAt(0).toUpperCase() + styleName.slice(1);
        button.style.cssText = `
            background: ${styleName === 'particles' ? 'rgba(139, 92, 246, 0.2)' : 'transparent'};
            color: white;
            border: 1px solid rgba(139, 92, 246, 0.3);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            transform-style: preserve-3d;
            transform: translateZ(0);
            backdrop-filter: blur(5px);
            font-weight: 500;
            font-size: 0.9rem;
            min-width: 90px;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        // Add hover effect
        button.onmouseover = () => {
            button.style.background = 'rgba(139, 92, 246, 0.3)';
            button.style.transform = 'translateZ(10px) scale(1.05)';
            button.style.boxShadow = '0 8px 20px rgba(139, 92, 246, 0.2)';
        };
        
        // Add mouseout effect
        button.onmouseout = () => {
            if (styleName !== style) {
                button.style.background = 'transparent';
            }
            button.style.transform = 'translateZ(0)';
            button.style.boxShadow = 'none';
        };
        
        // Add click effect
        button.onmousedown = () => {
            button.style.transform = 'translateZ(5px) scale(0.98)';
        };
        
        button.onmouseup = () => {
            button.style.transform = 'translateZ(10px) scale(1.05)';
        };
        
        button.onclick = () => {
            style = styleName;
            createParticles(styleName);
            // Update button styles
            switcher.querySelectorAll('button').forEach(btn => {
                btn.style.background = 'transparent';
                btn.style.transform = 'translateZ(0)';
                btn.style.boxShadow = 'none';
            });
            button.style.background = 'rgba(139, 92, 246, 0.2)';
            button.style.transform = 'translateZ(10px) scale(1.05)';
            button.style.boxShadow = '0 8px 20px rgba(139, 92, 246, 0.2)';
        };
        
        switcher.appendChild(button);
    });
    
    document.body.appendChild(switcher);
}

function onDocumentMouseMove(event) {
    mouseX = (event.clientX - windowHalfX);
    mouseY = (event.clientY - windowHalfY);
}

function onDocumentTouchStart(event) {
    if (event.touches.length === 1) {
        event.preventDefault();
        mouseX = event.touches[0].pageX - windowHalfX;
        mouseY = event.touches[0].pageY - windowHalfY;
    }
}

function onDocumentTouchMove(event) {
    if (event.touches.length === 1) {
        event.preventDefault();
        mouseX = event.touches[0].pageX - windowHalfX;
        mouseY = event.touches[0].pageY - windowHalfY;
    }
}

function onWindowResize() {
    windowHalfX = window.innerWidth / 2;
    windowHalfY = window.innerHeight / 2;
    
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function animate() {
    requestAnimationFrame(animate);
    
    targetX = mouseX * 0.0005; // Reduced mouse influence
    targetY = mouseY * 0.0005; // Reduced mouse influence
    
    particles.rotation.x += styles[style].speed;
    particles.rotation.y += styles[style].speed;
    
    // Add mouse interaction with reduced sensitivity
    particles.rotation.x += (targetY - particles.rotation.x) * 0.02;
    particles.rotation.y += (targetX - particles.rotation.y) * 0.02;
    
    // Update explosions
    updateExplosions();
    
    renderer.render(scene, camera);
}

// Initialize when the page loads
window.addEventListener('load', init); 