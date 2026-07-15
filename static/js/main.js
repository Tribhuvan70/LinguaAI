// Character counter for grammar textarea
const inputText = document.getElementById('inputText');
const charCount = document.getElementById('charCount');
if (inputText && charCount) {
  const update = () => {
    const n = inputText.value.length;
    charCount.textContent = `${n} character${n !== 1 ? 's' : ''}`;
  };
  inputText.addEventListener('input', update);
  update();
}

// Grammar form loading state
const grammarForm = document.getElementById('grammarForm');
const checkBtn = document.getElementById('checkBtn');
if (grammarForm && checkBtn) {
  grammarForm.addEventListener('submit', () => {
    checkBtn.disabled = true;
    checkBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Analyzing…';
  });
}

// Word of Day
async function loadWordOfDay() {
  const card = document.getElementById('wordOfDayCard');
  const content = document.getElementById('wordOfDayContent');
  card.classList.remove('d-none');
  content.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading word of the day…';
  try {
    const res = await fetch('/api/word_of_day');
    const d = await res.json();
    if (d.error) throw new Error(d.error);
    content.innerHTML = `
      <strong>📚 Word of the Day: ${d.word}</strong>
      <span class="badge bg-primary ms-2">${d.part_of_speech}</span><br/>
      <span class="text-muted">${d.definition}</span><br/>
      <em class="small">"${d.example}"</em><br/>
      <small class="text-muted">💡 ${d.tip}</small>`;
  } catch (e) {
    content.innerHTML = `<span class="text-danger">Could not load word of the day.</span>`;
  }
}

// Auto-dismiss alerts after 4 s
document.querySelectorAll('.alert-dismissible').forEach(a => {
  setTimeout(() => { const bs = bootstrap.Alert.getOrCreateInstance(a); bs && bs.close(); }, 4000);
});
