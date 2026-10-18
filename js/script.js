// Configuration
const CONFIG = {
    minConfidence: 0.6,
    silenceDelay: 2000, // ms to wait before finalizing a thought
    imageUpdateInterval: 5000 // ms minimum between image updates
};

// State
let isListening = false;
let recognition;
let lastTranscript = "";
let currentKeywords = [];
let lastImageKeyword = "";
let isFetchingImage = false;

// DOM Elements
const btnMic = document.getElementById('toggle-mic');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const transcriptBox = document.getElementById('transcript-box');
const keywordsContainer = document.getElementById('keywords-container');
const mainImage = document.getElementById('main-image');
const currentTopic = document.getElementById('current-topic');
const loadingBar = document.getElementById('loading-bar');
const placeholderArt = document.getElementById('placeholder-art');
const imageSource = document.getElementById('image-source');
const manualInput = document.getElementById('manual-input');
const btnManualSubmit = document.getElementById('btn-manual-submit');

// Stopwords List (Expanded)
const STOPWORDS = new Set([
    "a", "an", "the", "and", "or", "but", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "up", "down", "about", "into",
    "over", "after", "beneath", "under", "above", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "my", "your", "his", "her", "its", "our", "their",
    "me", "him", "us", "them", "what", "which", "who", "whom", "whose", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "can", "will", "just", "should", "now",
    "process", "development", "system", "example", "thing", "way", "part", "use", "make", "look",
    "like", "go", "come", "take", "see", "get", "give", "find", "tell", "ask", "work", "seem", "feel",
    "try", "leave", "call", "hello", "hey", "okay", "ok", "right", "well", "so", "basically", "actually"
]);

// --- Initialization ---
function init() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isListening = true;
            updateUIState(true);
        };

        recognition.onend = () => {
            if (isListening) {
                recognition.start(); // Auto-restart if supposed to be listening
            } else {
                updateUIState(false);
            }
        };

        recognition.onresult = handleSpeechResult;
        recognition.onerror = (event) => {
            console.error("Speech error:", event.error);
            if (event.error === 'not-allowed') {
                alert("Microphone access denied.");
                isListening = false;
                updateUIState(false);
            }
        };
    } else {
        alert("Web Speech API not supported in this browser. Please use Chrome or Edge.");
        btnMic.disabled = true;
    }

    btnMic.addEventListener('click', toggleListening);
}

function toggleListening() {
    if (isListening) {
        isListening = false;
        recognition.stop();
    } else {
        recognition.start();
    }
}

function updateUIState(listening) {
    if (listening) {
        btnMic.classList.add('active');
        btnMic.innerHTML = '<span class="icon">⏹</span> Stop Listening';
        statusDot.classList.add('listening');
        statusText.textContent = "Listening...";
    } else {
        btnMic.classList.remove('active');
        btnMic.innerHTML = '<span class="icon">▶</span> Start Listening';
        statusDot.classList.remove('listening');
        statusText.textContent = "Ready";
    }
}

// --- Core Logic ---

function handleSpeechResult(event) {
    let interimTranscript = '';
    let finalTranscript = '';

    for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
            processFinalText(event.results[i][0].transcript);
        } else {
            interimTranscript += event.results[i][0].transcript;
        }
    }

    // Update UI
    const displayHTML = `<span class="final">${lastTranscript}</span> <span class="interim" style="color: #aaa">${finalTranscript || interimTranscript}</span>`;
    // Only update if there's new content to avoid flickering
    if (finalTranscript) {
        lastTranscript += " " + finalTranscript;
        const p = document.createElement('p');
        p.textContent = finalTranscript;
        transcriptBox.appendChild(p);
        transcriptBox.scrollTop = transcriptBox.scrollHeight;
        
        // Remove placeholder if exists
        const placeholder = transcriptBox.querySelector('.placeholder');
        if (placeholder) placeholder.remove();
    }
}

async function processFinalText(text) {
    let keywords = [];
    try {
        const response = await fetch('/api/extract-keywords', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript: text })
        });
        if (response.ok) {
            const data = await response.json();
            if (data.keywords && data.keywords.length > 0) {
                keywords = data.keywords.map(k => typeof k === 'string' ? k : k.phrase);
            }
        }
    } catch (e) {
        console.warn('Backend NLP extraction unavailable, using client-side fallback:', e);
    }

    if (keywords.length === 0) {
        keywords = extractKeywords(text);
    }

    if (keywords.length > 0) {
        updateKeywordsUI(keywords);
        // Select best keyword for image
        const bestKeyword = keywords[0];
        if (bestKeyword && bestKeyword !== lastImageKeyword) {
            fetchImage(bestKeyword);
        }
    }
}

// --- NLP & Keyword Extraction ---

function extractKeywords(text) {
    const cleanText = text.toLowerCase().replace(/[^\w\s]/g, '');
    const words = cleanText.split(/\s+/).filter(w => w.length > 0);
    
    const candidates = {};

    // Helper to add candidate
    const add = (phrase, weight) => {
        if (!candidates[phrase]) candidates[phrase] = 0;
        candidates[phrase] += weight;
    };

    for (let i = 0; i < words.length; i++) {
        const w1 = words[i];
        
        // Unigrams (Low priority, only if significant length)
        if (!STOPWORDS.has(w1) && w1.length > 4) {
            add(w1, 1);
        }

        // Bigrams (Medium priority)
        if (i < words.length - 1) {
            const w2 = words[i+1];
            if (!STOPWORDS.has(w1) && !STOPWORDS.has(w2)) {
                add(`${w1} ${w2}`, 3);
            }
        }

        // Trigrams (High priority)
        if (i < words.length - 2) {
            const w2 = words[i+1];
            const w3 = words[i+2];
            // Allow middle word to be a stopword (e.g., "walking on two")
            if (!STOPWORDS.has(w1) && !STOPWORDS.has(w3)) {
                add(`${w1} ${w2} ${w3}`, 5);
            }
        }
    }

    // Sort by score
    return Object.entries(candidates)
        .sort((a, b) => b[1] - a[1])
        .map(entry => entry[0])
        .slice(0, 6); // Return top 6
}

function updateKeywordsUI(keywords) {
    // Prepend new keywords
    keywords.reverse().forEach(kw => {
        // Check if already exists recently to avoid dupes
        const existing = Array.from(keywordsContainer.children).slice(0, 5).map(c => c.textContent);
        if (!existing.includes(kw)) {
            const tag = document.createElement('div');
            tag.className = 'tag';
            tag.textContent = kw;
            tag.onclick = () => fetchImage(kw); // Manual override
            keywordsContainer.append(tag);
        }
    });

    // Limit total tags
    while (keywordsContainer.children.length > 15) {
        keywordsContainer.lastChild.remove();
    }
}

// --- Image Fetching Pipeline ---

async function fetchImage(keyword) {
    if (isFetchingImage) return; // Debounce
    isFetchingImage = true;
    lastImageKeyword = keyword;

    // UI Update
    currentTopic.textContent = keyword;
    loadingBar.classList.add('loading');
    loadingBar.style.width = '100%';

    // Strategy Pattern for Image Sources
    const strategies = [
        {
            name: 'SmartBoard AI Backend',
            url: async (k) => {
                const res = await fetch('/api/get-image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keyword: k })
                });
                if (!res.ok) throw new Error(`Backend response status ${res.status}`);
                const data = await res.json();
                return data.serve_url || data.image_url;
            },
            type: 'backend'
        },
        {
            name: 'Bing Thumbnail',
            // Use Bing's thumbnail API which is often open
            url: (k) => `https://tse2.mm.bing.net/th?q=${encodeURIComponent(k)}&w=1200&h=900&c=7&rs=1&p=0`,
            type: 'direct'
        },
        {
            name: 'Pollinations AI',
            // Generative AI fallback - guaranteed to work
            url: (k) => `https://image.pollinations.ai/prompt/${encodeURIComponent(k)}?width=1280&height=720&nologo=true`,
            type: 'direct'
        },
        {
            name: 'Unsplash Source',
            // Fallback (might be deprecated but worth a try)
            url: (k) => `https://source.unsplash.com/1600x900/?${encodeURIComponent(k)}`,
            type: 'direct'
        }
    ];

    let success = false;

    for (const strategy of strategies) {
        try {
            console.log(`Trying ${strategy.name} for "${keyword}"...`);
            const imageUrl = await Promise.resolve(strategy.url(keyword));
            if (!imageUrl) continue;
            
            // Validate image loads
            await validateImage(imageUrl);
            
            // If we get here, image is valid
            displayImage(imageUrl, strategy.name);
            success = true;
            break;
        } catch (e) {
            console.warn(`${strategy.name} failed:`, e);
            continue;
        }
    }

    if (!success) {
        currentTopic.textContent = `No image found for "${keyword}"`;
    }

    // Reset Loading
    loadingBar.classList.remove('loading');
    loadingBar.style.width = '0%';
    isFetchingImage = false;
}

function validateImage(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        const timeout = setTimeout(() => reject("Timeout"), 5000);
        
        img.onload = () => {
            clearTimeout(timeout);
            if (img.width > 50) resolve(url); // Ensure not a broken icon
            else reject("Image too small");
        };
        
        img.onerror = () => {
            clearTimeout(timeout);
            reject("Load error");
        };
        
        img.src = url;
    });
}

function displayImage(url, sourceName) {
    mainImage.style.display = 'block';
    placeholderArt.style.display = 'none';
    
    // Fade effect
    mainImage.style.opacity = 0;
    mainImage.src = url;
    
    mainImage.onload = () => {
        mainImage.style.opacity = 1;
        imageSource.textContent = `Source: ${sourceName}`;
        
        // Highlight active keyword
        const tags = document.querySelectorAll('.tag');
        tags.forEach(t => {
            if (t.textContent === lastImageKeyword) t.classList.add('active');
            else t.classList.remove('active');
        });
        setTimeout(nextImage, 8000);
    };
}

function nextImage() {
  const tags = Array.from(keywordsContainer.children);
  if (tags.length > 0) {
    const activeIndex = tags.findIndex(t => t.classList.contains('active'));
    let nextIndex;
    if (activeIndex === tags.length - 1) {
      // Stay on last keyword for repeated images
      nextIndex = activeIndex;
    } else {
      nextIndex = activeIndex + 1;
    }
    const nextKeyword = tags[nextIndex].textContent;
    fetchImage(nextKeyword);
  }
}

function handleManualSubmit() {
    if (!manualInput) return;
    const text = manualInput.value.trim();
    if (!text) return;

    // Add to transcript UI
    lastTranscript += " " + text;
    const p = document.createElement('p');
    p.textContent = text;
    transcriptBox.appendChild(p);
    transcriptBox.scrollTop = transcriptBox.scrollHeight;
    
    const placeholder = transcriptBox.querySelector('.placeholder');
    if (placeholder) placeholder.remove();

    processFinalText(text);
    manualInput.value = '';
}

if (btnManualSubmit && manualInput) {
    btnManualSubmit.addEventListener('click', handleManualSubmit);
    manualInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            handleManualSubmit();
        }
    });
}

// Start
init();
