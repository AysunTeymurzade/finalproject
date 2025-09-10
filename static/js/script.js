const form = document.getElementById("contact-form");
const alertDiv = document.getElementById("alert");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const data = {
    first_name: form.first_name.value,
    last_name: form.last_name.value,
    email: form.email.value,
    message: form.message.value,
    hp: form.hp.value
  };

  try {
    const res = await fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    });
    const result = await res.json();

    if (res.ok) {
      alertDiv.textContent = "Mesaj uğurla göndərildi!";
      alertDiv.style.color = "green";
      form.reset();
    } else {
      alertDiv.textContent = result.error || "Xəta baş verdi";
      alertDiv.style.color = "red";
    }
  } catch (err) {
    alertDiv.textContent = "Server xətası";
    alertDiv.style.color = "red";
  }
});
