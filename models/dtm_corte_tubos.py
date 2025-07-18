from odoo import fields,api,models
from datetime import datetime
from odoo.exceptions import ValidationError
import re


class Cortadora(models.Model):
    _name = "dtm.tubos.corte"
    _description = "Modulo para llevar el proceso de la cortadora de tubos"
    _rec_name = "orden_trabajo"

    orden_trabajo = fields.Integer(string="Orden de Trabajo", readonly=True)
    fecha_entrada = fields.Date(string="Fecha de entrada", readonly=True)
    nombre_orden = fields.Char(string="Nombre", readonly=True)
    cortadora_id = fields.One2many("dtm.tubos.documentos",'model_id', readonly=True)
    tipo_orden = fields.Char(string="Tipo", readonly=True)
    revision_ot = fields.Integer(string="VERSIÓN",readonly=True) # Esto es versión
    materiales_id = fields.Many2many("dtm.tubos.materiales", string="Materiales", readonly=True)

    def action_finalizar(self):
        cortes = self.cortadora_id.mapped('cortado')
        if len(set(cortes)) == 1 and False not in cortes:
            vals = {
                    "orden_trabajo": self.orden_trabajo,
                    "fecha_entrada": datetime.today(),
                    "nombre_orden": self.nombre_orden,
                    "revision_ot": self.revision_ot,
                    "materiales_id": self.materiales_id.ids,
                    "tipo_orden":self.tipo_orden

                }
            self.env['dtm.tubos.realizados'].create(vals)
            get_cortado = self.env['dtm.tubos.realizados'].search([('orden_trabajo','=',self.orden_trabajo),('revision_ot','=',self.revision_ot),('tipo_orden','=',self.tipo_orden)],limit=1)
            # print(get_cortado)
            for archivo in self.cortadora_id:
                # print(archivo)
                archivo.write({'model_id':None,'model2_id':get_cortado.id})

            # Actualiza el status en Procesos
            get_otp = self.env['dtm.proceso'].search([("ot_number","=",self.orden_trabajo),("revision_ot","=",self.revision_ot)])
            get_otp.write({
                "status":"doblado"
            })
            get_self = self.env['dtm.tubos.corte'].browse(self.id)
            get_self.unlink()
        else:
             raise ValidationError("Todos los nesteos deben estar cortados")

    def get_view(self, view_id=None, view_type='form', **options):
        res = super(Cortadora, self).get_view(view_id, view_type, **options)

        corte = self.env['dtm.tubos.corte'].search([('cortadora_id', '=', False)])
        if corte:
            corte.unlink()

        return res


class Documentos(models.Model):
    _name = "dtm.tubos.documentos"
    _description = "Se almacenan los archivos pdf con los cortes"

    model_id = fields.Many2one('dtm.tubos.corte')
    model2_id = fields.Many2one('dtm.tubos.realizados')

    documentos = fields.Binary()
    nombre = fields.Char(string="Nombre")
    contador = fields.Integer(string="Contador")
    cortado = fields.Boolean(string="Cortado")
    estado = fields.Char("Estado")

    def action_menos(self):
        self.contador -= 1
        if self.contador < 0:
            self.contador = 0

    def action_mas(self):
        self.contador += 1

    @api.onchange("cortado")
    def _action_cortado (self):
            get_laser = self.env['dtm.tubos.corte'].search([])
            for main in get_laser:
                for n_archivo in main.cortadora_id:
                    if self.nombre == n_archivo.nombre:
                        get_otp = self.env['dtm.proceso'].search([("ot_number","=",main.orden_trabajo),("tipe_order","=",main.tipo_orden)])
                        for documento in get_otp.tubos_id:
                            if documento.nombre == self.nombre:
                                get_self = self.env['dtm.tubos.documentos'].search([("id","=",self._origin.id)])
                                if self.cortado:
                                    get_self.write({
                                        "estado": "Material cortado"
                                    })
                                    self.estado = "Material cortado"
                                    documento.cortado = "Material cortado"
                                    get_otp.write({"status":"doblado"})
                                else:
                                    get_self.write({
                                        "estado": ""
                                    })
                                    self.estado = ""
                                    documento.cortado = ""

class Terminados(models.Model):
    _name = "dtm.tubos.materiales"
    _description = "Se guardan todos los cortes realizados"

    identificador = fields.Integer(string="Código")
    nombre = fields.Char(string="Materiales")
    medida = fields.Char(string="Medidas")
    cantidad = fields.Integer(string="Cantidad")
    inventario = fields.Integer(string="Inventario")
    requerido = fields.Integer(string="Requerido (Compras)")

class Realizado(models.Model):
    _name = "dtm.tubos.realizados"
    _description = "Modelo para lamacenar todas los cortes de tubos"
    _rec_name = "orden_trabajo"

    orden_trabajo = fields.Integer(string="Orden de Trabajo", readonly=True)
    revision_ot = fields.Integer(string="Versión",readonly=True) # Esto es versión
    fecha_entrada = fields.Date(string="Fecha de entrada", readonly=True)
    nombre_orden = fields.Char(string="Nombre", readonly=True)
    cortadora_id = fields.One2many("dtm.tubos.documentos",'model2_id', readonly=True)
    tipo_orden = fields.Char(string="Tipo", readonly=True)
    materiales_id = fields.Many2many("dtm.tubos.materiales", string="Materiales", readonly=True)
