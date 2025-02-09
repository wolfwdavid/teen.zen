const flashcards = [
  { question: 'How are you feeling today? :D ', answer: 'Madrid', avatar: 'avatar1.jpg' },
  { question: 'What is 2 + 2?', answer: '4', avatar: 'avatar2.jpg' },
  { question: 'What is the largest mammal?', answer: 'Blue whale', avatar: 'avatar3.jpg' },
  { question: 'What is the largest bone?', answer: 'Femur', avatar: 'avatar4.jpg' },
  // Add more questions as needed
];

const unsplashAccessKey = 'YOUR_UNSPLASH_ACCESS_KEY'; // Replace with your Unsplash API key

const backgroundElement = document.getElementById('background');
const flashcardContainer = document.getElementById('flashcard-container');

let currentCardIndex = 0;

function showCard(index) {
  const currentCard = flashcards[index];
  questionElement.textContent = currentCard.question;
  answerElement.textContent = '';
  avatarElement.src = currentCard.avatar;
}

function showAnswer() {
  // Your existing showAnswer function
}

function nextCard() {
  currentCardIndex = (currentCardIndex + 1) % flashcards.length;
  showCard(currentCardIndex);
}

function fetchRandomImage() {
  fetch(`https://api.unsplash.com/photos/random?client_id=${unsplashAccessKey}`)
    .then(response => response.json())
    .then(data => {
      const imageUrl = data.urls.regular;
      backgroundElement.style.backgroundImage = `url(${imageUrl})`;
    })
    .catch(error => console.error('Error fetching background image:', error));
}

function changeBackground() {
  fetchRandomImage();
  setInterval(fetchRandomImage, 5000); // Change background every 5 seconds
}

const avatarElement = document.getElementById('avatar');
const questionElement = document.getElementById('question');
const answerElement = document.getElementById('answer');
const answerInput = document.getElementById('answer');
const nextButton = document.getElementById('next-button');

nextButton.addEventListener('click', function() {
  showAnswer();
  // Move to the next card after showing the answer
  nextCard();
});

// Initial setup
showCard(currentCardIndex);
changeBackground();
