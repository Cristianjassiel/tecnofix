"""Formularios de las pantallas de Daniel; reutilizan los modelos comunes."""
from decimal import Decimal
from django import forms
from .forms import EstiloTailwindMixin
from .models import Cliente, Cotizacion, Estado, OrdenServicio


class ClienteForm(EstiloTailwindMixin, forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre_completo', 'telefono', 'correo', 'direccion']


class BuscarOrdenesForm(EstiloTailwindMixin, forms.Form):
    folio = forms.CharField(required=False, max_length=20)
    cliente = forms.CharField(required=False, max_length=150)
    serie = forms.CharField(label='Serie / IMEI', required=False, max_length=100)
    estado = forms.ChoiceField(required=False, choices=[('', 'Todos los estados'), *Estado.choices])
    fecha_inicio = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_fin = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

    def clean(self):
        data = super().clean()
        if data.get('fecha_inicio') and data.get('fecha_fin') and data['fecha_inicio'] > data['fecha_fin']:
            raise forms.ValidationError('La fecha inicial no puede ser posterior a la final.')
        return data


class ActualizarOrdenForm(EstiloTailwindMixin, forms.Form):
    nuevo_estado = forms.ChoiceField(required=False, choices=[])
    diagnostico_tecnico = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 4}))
    notas_reparacion = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
    costo_final = forms.DecimalField(required=False, min_value=0, max_digits=8, decimal_places=2)

    def __init__(self, *args, orden, **kwargs):
        super().__init__(*args, **kwargs)
        self.orden = orden
        destinos = {Estado.RECIBIDO: Estado.DIAGNOSTICO, Estado.ARREGLANDO: Estado.TERMINADO}
        choices = [('', 'Guardar notas sin cambiar estado')]
        if orden.estado in destinos:
            estado = destinos[orden.estado]
            choices.append((estado, estado.label))
        self.fields['nuevo_estado'].choices = choices

    def clean(self):
        data = super().clean()
        if data.get('nuevo_estado') == Estado.TERMINADO:
            if data.get('costo_final') is None:
                self.add_error('costo_final', 'Confirma el costo final antes de terminar.')
            elif self.orden.es_de_garantia and data['costo_final'] != Decimal('0'):
                self.add_error('costo_final', 'Una reparación por garantía no genera cobro.')
        return data


class CotizacionForm(EstiloTailwindMixin, forms.ModelForm):
    diagnostico_tecnico = forms.CharField(label='Diagnóstico', widget=forms.Textarea(attrs={'rows': 4}))

    class Meta:
        model = Cotizacion
        fields = ['costo_refaccion', 'costo_mano_obra', 'cargo_diagnostico']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.Meta.fields:
            self.fields[name].min_value = 0
            self.fields[name].widget.attrs['min'] = '0'

    def clean(self):
        data = super().clean()
        for name in self.Meta.fields:
            if data.get(name) is not None and data[name] < 0:
                self.add_error(name, 'El importe no puede ser negativo.')
        return data
