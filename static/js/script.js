const form = document.getElementById('contact-form');
const alertBox = document.getElementById('alert');
const submitBtn = document.getElementById('submitBtn');

function showAlert(type, message) {
  alertBox.className = 'alert ' + (type === 'success' ? 'success' : 'error');
  alertBox.textContent = message;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const name = document.getElementById('name').value.trim();
  const email = document.getElementById('email').value.trim();
  const message = document.getElementById('message').value.trim();
  const hp = document.getElementById('hp').value.trim();

  submitBtn.disabled = true;
  submitBtn.textContent = 'Göndərilir...';

  try {
    const res = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, message, hp }),
    });
    const data = await res.json();

    if (!res.ok) {
      showAlert('error', data.error || 'Xəta baş verdi.');
    } else {
      showAlert('success', 'Mesaj qəbul olundu!');
      form.reset();
    }
  } catch (err) {
    showAlert('error', 'Şəbəkə xətası.');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Göndər';
  }
});
