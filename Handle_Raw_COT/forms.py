# cot/forms.py
# ─────────────────────────────────────────────────────────────────────────────
# Does NOT use ClearableFileInput anywhere.
# Works on Python 3.7 + Django 2.x / 3.x / 4.x / 5.x
# ─────────────────────────────────────────────────────────────────────────────

from django import forms


# ─────────────────────────────────────────────────────────────────────────────
# Custom widget — plain FileInput with multiple attribute
# We build this from scratch so no Django internal ever sees
# "multiple=True" on a ClearableFileInput.
# ─────────────────────────────────────────────────────────────────────────────

class MultipleFileInput(forms.FileInput):
    """
    Renders:  <input type="file" name="files" multiple accept=".htm,.html,.xls,.xlsx,.xlsb,.csv,.ods">

    Inherits from forms.FileInput (NOT ClearableFileInput).
    ClearableFileInput raises ValueError on multiple=True in older Django.
    """
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        final_attrs = {"accept": ".htm,.html,.xls,.xlsx,.xlsb,.csv,.ods", "multiple": "multiple"}
        if attrs:
            final_attrs.update(attrs)
        # Call parent FileInput.__init__ — never touches ClearableFileInput
        super(MultipleFileInput, self).__init__(attrs=final_attrs)

    def value_from_datadict(self, data, files, name):
        """
        Django's FileField.clean() expects a single file object, not a list.
        Return the first file here so Django validation passes.
        The VIEW always uses request.FILES.getlist(name) to get ALL files.
        """
        file_list = files.getlist(name)
        if file_list:
            return file_list[0]
        return None

    def use_required_attribute(self, initial_value):
        # Never add 'required' on a file input — handled by clean()
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Custom field — wraps MultipleFileInput, skips all ClearableFileInput paths
# ─────────────────────────────────────────────────────────────────────────────

class MultipleFileField(forms.FileField):
    """
    A FileField whose widget is always MultipleFileInput.
    Overrides __init__ so that no code path can accidentally
    swap in a ClearableFileInput.
    """

    def __init__(self, *args, **kwargs):
        # Force our widget regardless of what the caller passes
        kwargs["widget"] = MultipleFileInput()
        super(MultipleFileField, self).__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        # data is the first file (from value_from_datadict).
        # Run the standard FileField validation on it.
        return super(MultipleFileField, self).clean(data, initial)


# ─────────────────────────────────────────────────────────────────────────────
# The actual form
# ─────────────────────────────────────────────────────────────────────────────

class CotUploadForm(forms.Form):
    """
    Form for uploading one or more CFTC COT .htm files.

    IMPORTANT — reading all files in the view:
        Because Django's FileField only validates one file,
        always read the full list in the view like this:

            uploaded_files = request.FILES.getlist("files")

        Never rely on form.cleaned_data["files"] for the complete list —
        it only contains the first selected file.
    """

    files = MultipleFileField(
        label="CFTC Files",
        help_text=(
            "Select one or more CFTC files: HTML (.htm/.html) for current reports, "
            "or Excel (.xls/.xlsx/.xlsb/.csv/.ods) for historical data. "
            "HTML: deacmesf.htm (FX + Bitcoin), deacmxsf.htm (Gold + Silver). "
            "Excel: Download from https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/"
        ),
        required=True,
    )

    def clean_files(self):
        """
        Validates the first file Django sees.
        Extension must be .htm, .html, .xls, .xlsx, .xlsb, .csv, or .ods.
        All other files are validated individually in the view.
        """
        f = self.cleaned_data.get("files")
        if not f:
            raise forms.ValidationError("Please select at least one file.")

        name = f.name.lower()
        valid_exts = (".htm", ".html", ".xls", ".xlsx", ".xlsb", ".csv", ".ods")
        if not name.endswith(valid_exts):
            raise forms.ValidationError(
                "Only .htm, .html, .xls, .xlsx, .xlsb, .csv, or .ods files are accepted. Received: {}".format(f.name)
            )
        return f