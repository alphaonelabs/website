document.addEventListener('DOMContentLoaded', function() {
    // Add new question
    document.getElementById('add-question').addEventListener('click', function() {
        const newQuestion = document.createElement('div');
        newQuestion.className = 'question bg-gray-50 dark:bg-gray-700/50 p-4 rounded-lg border border-gray-200 dark:border-gray-600';
        newQuestion.innerHTML = `
    <div class="flex justify-between items-center mb-3">
      <select name="question_type[]" class="question-type-selector p-2 border rounded-md bg-white dark:bg-gray-800" required>
        <option value="mcq">Multiple Choice</option>
        <option value="checkbox">Checkbox</option>
        <option value="text">Text</option>
        <option value="true_false">True/False</option>
        <option value="scale">Scale</option>
      </select>
      <button type="button" class="remove-question text-red-500 hover:text-red-700">×</button>
    </div>
    <input type="text" name="question_text[]" placeholder="Question text" required class="w-full p-2 mb-3 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800" />
    <div class="choices-section">
      <textarea name="question_choices[]" placeholder="Enter choices (one per line)" class="choices-input w-full p-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800" rows="4"></textarea>
      <div class="scale-fields hidden mt-2">
        <input type="number" name="scale_min[]" placeholder="Min" min="1" max="99" class="w-1/2 p-2 mr-2 border rounded-md" />
        <input type="number" name="scale_max[]" placeholder="Max" min="2" max="100" class="w-1/2 p-2 ml-2 border rounded-md" />
      </div>
    </div>
    `;
        // Add type change handler
        newQuestion.querySelector('.question-type-selector').addEventListener('change', handleTypeChange);

        // Add validation feedback for question text
        const questionText = newQuestion.querySelector('input[name="question_text[]"]');
        questionText.addEventListener('invalid', function() {
            if (!this.validity.valid) {
                this.classList.add('border-red-500');

                // Add or update error message
                let errorMsg = this.parentNode.querySelector('.question-error');
                if (!errorMsg) {
                    errorMsg = document.createElement('div');
                    errorMsg.className = 'question-error text-sm text-red-600 mt-1';
                    this.after(errorMsg);
                }
                errorMsg.textContent = 'Please enter a question text';
            }
        });

        questionText.addEventListener('input', function() {
            if (this.validity.valid) {
                this.classList.remove('border-red-500');
                const errorMsg = this.parentNode.querySelector('.question-error');
                if (errorMsg) errorMsg.remove();
            }
        });
        document.getElementById('questions').appendChild(newQuestion);
    });

    function validateScaleValues(input) {
        const parent = input.closest('.scale-fields');
        const min = parseInt(parent.querySelector('input[name="scale_min[]"]').value);
        const max = parseInt(parent.querySelector('input[name="scale_max[]"]').value);

        if (min && max && min >= max) {
            alert('Maximum value must be greater than minimum value');
            input.value = '';
        }
    }
    // Handle type changes
    function handleTypeChange(event) {
        const parent = event.target.closest('.question');
        const choicesInput = parent.querySelector('.choices-input');
        const scaleFields = parent.querySelector('.scale-fields');
        const scaleMin = parent.querySelector('input[name="scale_min[]"]');
        const scaleMax = parent.querySelector('input[name="scale_max[]"]');

        switch (event.target.value) {
            case 'text':
                choicesInput.placeholder = 'Not needed for text questions';
                choicesInput.disabled = true;
                choicesInput.required = false;
                scaleFields.classList.add('hidden');
                if (scaleMin) scaleMin.required = false;
                if (scaleMax) scaleMax.required = false;
                break;
            case 'true_false':
                choicesInput.placeholder = 'Choices will be automatically generated';
                choicesInput.disabled = true;
                choicesInput.required = false;
                scaleFields.classList.add('hidden');
                if (scaleMin) scaleMin.required = false;
                if (scaleMax) scaleMax.required = false;
                break;
            case 'scale':
                choicesInput.placeholder = 'Not needed for scale questions';
                choicesInput.disabled = true;
                choicesInput.required = false;
                scaleFields.classList.remove('hidden');
                if (scaleMin) scaleMin.required = true;
                if (scaleMax) scaleMax.required = true;
                break;
            default: // mcq or checkbox
                choicesInput.placeholder = 'Enter choices (one per line)';
                choicesInput.disabled = false;
                choicesInput.required = true;
                scaleFields.classList.add('hidden');
                if (scaleMin) scaleMin.required = false;
                if (scaleMax) scaleMax.required = false;
        }
    }

    // Add initial event listeners and trigger initial setup
    document.querySelectorAll('.question-type-selector').forEach(select => {
        select.addEventListener('change', handleTypeChange);
        // Initialize the form based on the initial selection
        handleTypeChange({
            target: select
        });
    });

    // Remove question
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-question')) {
            e.target.closest('.question').remove();
        }
    });
});
