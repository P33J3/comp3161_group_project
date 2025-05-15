document.addEventListener('DOMContentLoaded', function () {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.display = 'none';
        }, 5000); // Auto-dismiss after 5 seconds
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function (event) {
            const inputs = form.querySelectorAll('input[required]');
            let isValid = true;
            inputs.forEach(input => {
                if (!input.value.trim()) {
                    isValid = false;
                    input.classList.add('is-invalid');
                } else {
                    input.classList.remove('is-invalid');
                }
            });
            if (!isValid) {
                event.preventDefault();
                alert('Please fill out all required fields.');
            }
        });
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const registerForm = document.querySelector('#registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(registerForm);
            fetch(registerForm.action, {
                method: 'POST',
                body: formData,
            })
                .then(response => response.json())
                .then(data => {
                    if (data.message) {
                        alert(data.message);
                        if (data.success) {
                            window.location.reload();
                        }
                    }
                })
                .catch(error => console.error('Error:', error));
        });
    }
});