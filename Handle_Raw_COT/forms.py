from django import forms


class CotUploadForm(forms.Form):
    files = forms.FileField(
        widget=forms.ClearableFileInput(attrs={"multiple": True}),
        label="CFTC HTML Files",
        help_text="Select one or more downloaded CFTC .htm files (e.g. deacmesf.htm, deacmxsf.htm)",
    )

    def clean_files(self):
        # Django only exposes the last file through cleaned_data["files"]
        # when multiple=True — we handle all files in the view via request.FILES.getlist()
        # This clean just validates the single file Django sees.
        f = self.cleaned_data["files"]
        name = f.name.lower()
        if not (name.endswith(".htm") or name.endswith(".html")):
            raise forms.ValidationError("Only .htm / .html files are accepted.")
        return f
    

    