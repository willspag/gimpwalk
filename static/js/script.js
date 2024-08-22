document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const loadingElement = document.getElementById('loading');
    const responseElement = document.getElementById('response');
    const responseContentElement = document.getElementById('response-content');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        loadingElement.classList.remove('hidden');
        responseElement.classList.add('hidden');
        
        fetch('/', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            loadingElement.classList.add('hidden');
            responseElement.classList.remove('hidden');
            
            if (data.error) {
                responseContentElement.innerHTML = `<p class="error">${data.error}</p>`;
            } else {
                responseContentElement.innerHTML = marked(data.response);
            }
        })
        .catch(error => {
            loadingElement.classList.add('hidden');
            responseElement.classList.remove('hidden');
            responseContentElement.innerHTML = `<p class="error">An error occurred: ${error.message}</p>`;
            console.error('Error:', error);
        });
    });
});