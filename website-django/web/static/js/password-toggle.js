function togglePasswordVisibility(inputId, toggleId) {
  const passwordInput = document.getElementById(inputId);
  const toggleButton = document.getElementById(toggleId);
  const eyeIcon = toggleButton.querySelector("i");

  if (passwordInput.type === "password") {
    passwordInput.type = "text";
    eyeIcon.classList.remove("fa-eye");
    eyeIcon.classList.add("fa-eye-slash");
  } else {
    passwordInput.type = "password";
    eyeIcon.classList.remove("fa-eye-slash");
    eyeIcon.classList.add("fa-eye");
  }
}

// Initialize password toggles when the document is loaded
document.addEventListener("DOMContentLoaded", function () {
  const passwordFields = document.querySelectorAll('input[type="password"]');

  passwordFields.forEach((field) => {
    const fieldId = field.id;
    const toggleId = `${fieldId}-toggle`;

    // Create toggle button
    const toggleButton = document.createElement("button");
    toggleButton.id = toggleId;
    toggleButton.type = "button";
    toggleButton.className =
      "absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 focus:outline-none";
    toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
    toggleButton.onclick = () => togglePasswordVisibility(fieldId, toggleId);

    // Create wrapper div if not exists
    let wrapper = field.parentElement;
    if (!wrapper.classList.contains("relative")) {
      wrapper = document.createElement("div");
      wrapper.className = "relative";
      field.parentNode.insertBefore(wrapper, field);
      wrapper.appendChild(field);
    }

    // Add toggle button
    wrapper.appendChild(toggleButton);
  });
});
