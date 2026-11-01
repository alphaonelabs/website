from captcha.fields import CaptchaTextInput
from django import forms


class TailwindInput(forms.TextInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                )
            }
        )


class TailwindTextarea(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                ),
                "rows": kwargs.pop("rows", 4),
            }
        )


class TailwindEmailInput(forms.EmailInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                )
            }
        )


class TailwindNumberInput(forms.NumberInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                )
            }
        )


class TailwindSelect(forms.Select):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                    "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                    "border-gray-300 dark:border-gray-600"
                )
            }
        )


class TailwindCheckboxInput(forms.CheckboxInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "h-4 w-4 rounded border-gray-300 text-teal-600 focus:ring-teal-500 "
                    "dark:border-gray-600 dark:bg-gray-800 dark:ring-offset-gray-800"
                )
            }
        )


class TailwindFileInput(forms.FileInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 "
                    "file:rounded file:border-0 file:text-sm file:font-semibold file:bg-teal-50 "
                    "file:text-teal-700 hover:file:bg-teal-100 dark:file:bg-teal-900 "
                    "dark:file:text-teal-200 dark:text-gray-400"
                )
            }
        )


class TailwindDateTimeInput(forms.DateTimeInput):
    def __init__(self, *args, **kwargs):
        kwargs["format"] = "%Y-%m-%dT%H:%M"  # HTML5 datetime-local format
        super().__init__(*args, **kwargs)
        self.attrs.update(
            {
                "class": (
                    "block w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 "
                    "focus:ring-blue-500 dark:bg-gray-700 "
                    "border-gray-300 dark:border-gray-600 dark:text-white cursor-pointer"
                ),
                "type": "datetime-local",
                "placeholder": "Select date and time",
                "required": True,
                "autocomplete": "off",
            }
        )


class TailwindCaptchaTextInput(CaptchaTextInput):
    template_name = "captcha/widget.html"

    def __init__(self, attrs=None):
        default_attrs = {
            "class": (
                "block w-full border rounded p-2 focus:outline-none focus:ring-2 "
                "focus:ring-teal-300 dark:focus:ring-teal-800 bg-white dark:bg-gray-800 "
                "border-gray-300 dark:border-gray-600"
            ),
            "placeholder": "Enter CAPTCHA",
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
