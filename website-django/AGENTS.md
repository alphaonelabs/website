start with 5 emojis that best describe what you are about to do and one word on how you're feeling

# HTML Styling Rules
- Always use Tailwind CSS classes for styling HTML elements
- Never use custom CSS classes
- Never use inline styles
- Follow the project's color scheme using Tailwind's color classes:
  - Primary: teal-300
  - Secondary: gray-600
  - Success: green-600
  - Warning: yellow-600
  - Danger: red-600
  - Dark mode variants using dark: prefix

# Common Component Patterns
- Containers: container mx-auto px-4
- Cards: bg-white dark:bg-gray-800 rounded-lg shadow-lg
- Forms:
  - Inputs: w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500
  - Labels: block text-sm font-medium text-gray-700 dark:text-gray-300
  - Buttons:
    - Primary: bg-teal-300 hover:bg-teal-400 text-white px-6 py-2 rounded-lg transition duration-200
    - Secondary: bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300
- Typography:
  - Headings: text-2xl font-bold (adjust size as needed)
  - Body: text-gray-600 dark:text-gray-300
  - Links: text-blue-600 hover:text-blue-800 dark:text-blue-400

# Layout
- Use flex and grid for layouts
- Consistent spacing with gap-{size} and space-{y|x}-{size}
- Responsive design using sm:, md:, lg:, xl: prefixes

# Dark Mode
- Always include dark mode alternatives using dark: prefix
- Use dark:bg-gray-800 for card backgrounds
- Use dark:text-gray-300 for text

# Accessibility
- Use proper heading hierarchy
- Include proper ARIA labels where needed
- Ensure sufficient color contrast
- Add hover/focus states for interactive elements

# file locations

the setting.py file is in the web folder
the urls.py file is in the web folder
the views.py file is in the web folder
the models.py file is in the web folder
the tests are in the tests folder
the admin.py file is in the web folder

make sure to fix the linting errors
dont create .md files
