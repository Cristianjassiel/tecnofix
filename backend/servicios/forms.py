"""Formularios del sistema."""

from django import forms

from .models import Accesorio, Cliente, Equipo, OrdenServicio

# Clases de Tailwind que comparten todos los campos, para no repetirlas.
INPUT = (
    "mt-1 w-full rounded-lg border border-stone-300 p-2 "
    "focus:border-indigo-500 focus:outline-none"
)
SELECT = (
    "mt-1 w-full rounded-lg border border-stone-300 bg-white p-2 "
    "focus:border-indigo-500 focus:outline-none"
)


class MultipleFileInput(forms.ClearableFileInput):
    """Permite seleccionar varias fotos a la vez.

    Django bloquea `multiple` en el widget normal, así que hay que declararlo
    aparte. Los archivos se leen en la vista con request.FILES.getlist().
    """

    allow_multiple_selected = True


class EstiloTailwindMixin:
    """Aplica las clases de Tailwind a todos los campos del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs.setdefault("class", SELECT)
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "h-4 w-4 accent-indigo-600")
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                pass
            elif isinstance(widget, forms.ClearableFileInput):
                widget.attrs.setdefault(
                    "class",
                    "block w-full text-sm text-stone-500 file:mr-4 file:rounded-lg "
                    "file:border-0 file:bg-stone-200 file:px-4 file:py-2 "
                    "file:text-sm file:text-stone-800 hover:file:bg-stone-300",
                )
            else:
                widget.attrs.setdefault("class", INPUT)


class EquipoForm(EstiloTailwindMixin, forms.ModelForm):
    class Meta:
        model = Equipo
        fields = ["cliente", "tipo", "marca", "modelo", "numero_serie", "color"]


class NuevaOrdenForm(EstiloTailwindMixin, forms.Form):
    """Formulario de recepción: cliente, equipo, accesorios, falla y asignación.

    Captura todo en una sola pantalla. Si el cliente es nuevo, sus datos se
    guardan aquí mismo sin pasar por otra pantalla.
    """

    # Cliente
    cliente_existente = forms.ModelChoiceField(
        label="Cliente existente",
        queryset=Cliente.objects.all(),
        required=False,
        empty_label="Selecciona un cliente registrado",
    )
    nuevo_nombre = forms.CharField(label="Nombre completo", max_length=150, required=False)
    nuevo_telefono = forms.CharField(label="Teléfono", max_length=20, required=False)
    nuevo_correo = forms.EmailField(label="Correo electrónico", required=False)

    # Equipo
    tipo = forms.ChoiceField(label="Tipo de dispositivo", choices=Equipo.Tipo.choices)
    marca = forms.CharField(max_length=50)
    modelo = forms.CharField(max_length=50)
    numero_serie = forms.CharField(label="Número de serie o IMEI", max_length=100)

    # Accesorios
    accesorios = forms.ModelMultipleChoiceField(
        label="Accesorios entregados",
        queryset=Accesorio.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    otros_accesorios = forms.CharField(
        label="Otros accesorios (especifica cuál)", max_length=200, required=False
    )

    # Orden
    falla_reportada = forms.CharField(
        label="Describe la falla con las palabras del cliente",
        widget=forms.Textarea(attrs={"rows": 4}),
    )
    tecnico = forms.ModelChoiceField(
        label="Técnico asignado",
        queryset=None,  # se llena en __init__
        empty_label="Selecciona un técnico",
    )
    prioridad = forms.ChoiceField(
        label="Prioridad",
        choices=OrdenServicio.Prioridad.choices,
        initial=OrdenServicio.Prioridad.NORMAL,
        widget=forms.RadioSelect,
    )
    fotos = forms.ImageField(
        label="Fotos del equipo al recibirlo",
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True}),
    )

    def __init__(self, *args, **kwargs):
        tecnicos = kwargs.pop("tecnicos", None)
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User

        self.fields["tecnico"].queryset = (
            tecnicos if tecnicos is not None else User.objects.none()
        )

    def clean(self):
        datos = super().clean()
        cliente = datos.get("cliente_existente")
        nombre = (datos.get("nuevo_nombre") or "").strip()
        telefono = (datos.get("nuevo_telefono") or "").strip()

        if not cliente and not nombre:
            raise forms.ValidationError(
                "Selecciona un cliente registrado o captura los datos de uno nuevo."
            )
        if not cliente and not telefono:
            self.add_error(
                "nuevo_telefono", "El teléfono es obligatorio para un cliente nuevo."
            )
        return datos
