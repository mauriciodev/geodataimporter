from django.db import models
from django.conf import settings
from django.contrib.gis.db import models as geomodels
import uuid

# ========================================
# Índice de produtos geoespaciais
# ========================================
class ProductIndex(models.Model):
    area = geomodels.MultiPolygonField()
    metadataid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    date = models.DateField()
    scale = models.IntegerField()
    file_path = models.FilePathField(path='.')  # caminho relativo, pode ser ajustado conforme o servidor

    def __str__(self):
        return f"{self.metadataid}: {self.file_path}"


# ========================================
# Histórico de importação/exclusão
# ========================================
class HistoricoImportacaoExclusao(models.Model):
    ACAO_CHOICES = [
        ('adicionado', 'Adicionado'),
        ('removido', 'Removido'),
    ]

    metadata_id = models.CharField(max_length=256)
    classe = models.CharField(max_length=256, null=True, blank=True)
    acao = models.CharField(max_length=10, choices=ACAO_CHOICES)
    data_evento = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    detalhes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.acao.capitalize()} {self.metadata_id} ({self.classe or 'todas classes'}) em {self.data_evento.strftime('%d/%m/%Y %H:%M:%S')}"


# ========================================
# Produtos geoespaciais
# ========================================
class ProdutoGeoespacial(models.Model):
    metadata_id = models.CharField(max_length=256, unique=True)
    nome_arquivo = models.CharField(max_length=256)
    data_do_produto = models.DateField(null=True, blank=True)
    data_importacao = models.DateTimeField(auto_now_add=True)
    esquema = models.CharField(max_length=256, null=True, blank=True)
    escala = models.CharField(max_length=64, null=True, blank=True)
    area_mapeada = geomodels.PolygonField(null=True, blank=True, srid=4326)

    def __str__(self):
        return f"{self.metadata_id} ({self.data_do_produto})"


# ========================================
# Representação gráfica das classes
# ========================================
class RepresentacaoGrafica(models.Model):
    TIPO_GRUPO_CHOICES = [
        ('ferrovia', 'Ferrovia'),
        ('rodovia', 'Rodovia'),
        ('drenagem', 'Trecho de Drenagem'),
        ('edificacao', 'Edificação'),
        ('limite', 'Limite Administrativo'),
        ('vegetacao', 'Vegetação'),
        ('corpo_dagua', 'Corpo dÁgua'),
        ('ponte', 'Ponte/Viaduto'),
        ('aeroporto', 'Aeroporto'),
        ('energia', 'Energia/Transmissão'),
        ('saneamento', 'Saneamento'),
        ('outros', 'Outros'),
    ]

    # Mapeamento completo das classes ET-EDGV 2.1.3 e 3.0 para grupo gráfico
    EDGV_GRUPO_MAP = {
        # 2.1.3
        "HID_Massa_Dagua_A": "corpo_dagua",
        "HID_Trecho_Drenagem_L": "drenagem",
        "LOC_Area_Edificada_A": "edificacao",
        "LOC_Nome_Local_P": "limite",
        "TRA_Arruamento_L": "rodovia",
        "TRA_Ponte_L": "ponte",
        "TRA_Trecho_Ferroviario_L": "ferrovia",
        "TRA_Trecho_Rodoviario_L": "rodovia",
        "VEG_Campo_A": "vegetacao",
        "VEG_Floresta_A": "vegetacao",

        # 3.0
        "CBGE_Area_Duto_A": "outros",
        "CBGE_Cemiterio_A": "outros",
        "CBGE_Cemiterio_P": "outros",
        "CBGE__Trecho_Arruamento_L": "rodovia",
        "EDF_Edif_Abast_Agua_P": "saneamento",
        "EDF_Edif_Agropec_Ext_Vegetal_Pesca_A": "edificacao",
        "EDF_Edif_Agropec_Ext_Vegetal_Pesca_P": "edificacao",
        "EDF_Edif_Constr_Lazer_P": "edificacao",
        "EDF_Edif_Constr_Turistica_P": "edificacao",
        "EDF_Edif_Desenv_Social_P": "edificacao",
        "EDF_Edif_Energia_P": "energia",
        "EDF_Edif_Ensino_A": "edificacao",
        "EDF_Edif_Ensino_P": "edificacao",
        "EDF_Edif_Industrial_A": "edificacao",
        "EDF_Edif_Industrial_P": "edificacao",
        "EDF_Edif_Metro_Ferroviaria_P": "ferrovia",
        "EDF_Edif_Policia_P": "edificacao",
        "EDF_Edif_Pub_Civil_P": "edificacao",
        "EDF_Edif_Pub_Militar_P": "edificacao",
        "EDF_Edif_Religiosa_P": "edificacao",
        "EDF_Edif_Rodoviaria_P": "rodovia",
        "EDF_Edif_Saneamento_P": "saneamento",
        "EDF_Edif_Saude_P": "edificacao",
        "EDF_Edificacao_A": "edificacao",
        "EDF_Edificacao_P": "edificacao",
        "ENC_Subest_Transm_Distrib_Energia_Eletrica_A": "energia",
        "ENC_Torre_Comunic_P": "energia",
        "ENC_Torre_Energia_P": "energia",
        "ENC_Trecho_Energia_L": "energia",
        "FER_Trecho_Ferroviario_L": "ferrovia",
        "HID_Barragem_L": "corpo_dagua",
        "HID_Sumidouro_Vertedouro_P": "corpo_dagua",
        "LAZ_Campo_Quadra_A": "vegetacao",
        "LAZ_Campo_Quadra_P": "vegetacao",
        "LML_Area_Desamente_Edificada_A": "edificacao",
        "LML_Nome_Local_P": "limite",
        "LML_Posic_Geo_Localidade_P": "limite",
        "LML_Unidade_Federacao_A": "limite",
        "REL_Curva_Nivel_L": "outros",
        "REL_Elemento_Fisiografica_Natural_L": "outros",
        "REL_Ponto_Cotado_Altimetrico_P": "outros",
        "ROD_Trecho_Rodoviario": "rodovia",
        "TRA_Caminho_Carrocavel_L": "rodovia",
        "TRA_Passagem_Elevada_Viaduto_L": "ponte",
        "TRA_Passagem_Elevada_Viaduto_P": "ponte",
        "TRA_Ponte_P": "ponte",
        "TRA_Travessia_Pedestre_P": "ponte",
        "TRA_Tunel_L": "rodovia",
        "TRA_Tunel_P": "rodovia",
        "VEG_Veg_Cultivada_A": "vegetacao",
    }

    esquema = models.CharField(max_length=256)
    classe = models.CharField(max_length=256)
    grupo_representacao = models.CharField(
        max_length=50, choices=TIPO_GRUPO_CHOICES, default='outros'
    )

    class Meta:
        unique_together = ['esquema', 'classe']
        verbose_name = 'Representação Gráfica'
        verbose_name_plural = 'Representações Gráficas'

    def save(self, *args, **kwargs):
        # Preenche automaticamente o grupo gráfico pelo mapeamento
        if not self.grupo_representacao or self.grupo_representacao == 'outros':
            self.grupo_representacao = self.EDGV_GRUPO_MAP.get(self.classe, 'outros')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.classe} ({self.esquema}) - {self.get_grupo_representacao_display()}"
