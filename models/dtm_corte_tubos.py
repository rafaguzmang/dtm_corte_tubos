from odoo import fields,api,models
from datetime import datetime
from odoo.exceptions import ValidationError
import re


class Cortadora(models.Model):
    _name = "dtm.tubos.corte"
    _description = "Modulo para llevar el proceso de la cortadora de tubos"

    orden_trabajo = fields.Integer(string="Orden de Trabajo", readonly=True)
    fecha_entrada = fields.Date(string="Fecha de entrada", readonly=True)
    nombre_orden = fields.Char(string="Nombre", readonly=True)
    cortadora_id = fields.Many2many("dtm.tubos.documentos", readonly=True)
    tipo_orden = fields.Char(string="Tipo", readonly=True)
    materiales_id = fields.Many2many("dtm.tubos.materiales", string="Materiales", readonly=True)

    def action_finalizar(self):
        get_otp = self.env['dtm.proceso'].search([("ot_number","=",self.orden_trabajo),("tipe_order","=","OT")])
        get_otd = self.env['dtm.odt'].search([("ot_number","=",self.orden_trabajo)]) # Actualiza el status en los modelos odt y proceso a corte
        cont = 0;
        for corte in self.cortadora_id:
            if corte.estado != "Material cortado":
              break
            cont +=1
        if cont == 0:
             get_otd.write({"status":"Corte"})
             get_otp.write({"status":"corte"})
        else:
            get_otd.write({"status":"Corte - Doblado"})
            get_otp.write({"status":"cortedoblado"})
        if len(self.cortadora_id) == cont:
            vals = {
                "orden_trabajo": self.orden_trabajo,
                "fecha_entrada": datetime.today(),
                "nombre_orden": self.nombre_orden,
            }
            get_info = self.env['dtm.tubos.realizados'].search([])
            get_info.create(vals)
            get_otd = self.env['dtm.odt'].search([("ot_number","=",self.orden_trabajo)]) # Actualiza el status en los modelos odt y proceso a corte
            get_otd.write({"status":"Doblado"})
            get_otp = self.env['dtm.proceso'].search([("ot_number","=",self.orden_trabajo),("tipe_order","=","OT")])
            get_otp.write({
                "status":"doblado"
            })
            get_info =  self.env['dtm.tubos.realizados'].search([("orden_trabajo","=", self.orden_trabajo)])
            lines = []
            for docs in self.cortadora_id:
                line = (0,get_info.id,{
                    "nombre": docs.nombre,
                    "documentos":docs.documentos,
                })
                lines.append(line)
            get_info.cortadora_id = lines

            for material in self.materiales_id:
                get_almacen = self.env['dtm.materiales.solera'].search([("codigo","=","0")])
                if re.match("Solera",material.nombre):
                    get_almacen = self.env['dtm.materiales.solera'].search([("codigo","=",material.identificador)])
                elif re.match("Ángulo",material.nombre):
                    get_almacen = self.env['dtm.materiales.angulos'].search([("codigo","=",material.identificador)])
                elif re.match("Perfil",material.nombre):
                    get_almacen = self.env['dtm.materiales.perfiles'].search([("codigo","=",material.identificador)])
                elif re.match("Canal",material.nombre):
                    get_almacen = self.env['dtm.materiales.canal'].search([("codigo","=",material.identificador)])
                elif re.match("Tubo",material.nombre):
                    get_almacen = self.env['dtm.materiales.tubos'].search([("codigo","=",material.identificador)])

                cantidad = get_almacen.cantidad - material.cantidad
                apartado = get_almacen.apartado - material.cantidad
                vals = {
                    "cantidad":cantidad,
                    "apartado":apartado,
                    "disponible":cantidad - apartado,
                }
                get_almacen.write(vals)
            get_self = self.env['dtm.tubos.corte'].browse(self.id)
            get_self.unlink()
        else:
             raise ValidationError("Todos los nesteos deben estar cortados")


class Documentos(models.Model):
    _name = "dtm.tubos.documentos"
    _description = "Se almacenan los archivos pdf con los cortes"

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
                        get_otd = self.env['dtm.odt'].search([("ot_number","=",main.orden_trabajo)]) # Actualiza el status en los modelos odt y proceso a corte
                        get_otp = self.env['dtm.proceso'].search([("ot_number","=",main.orden_trabajo),("tipe_order","=",main.tipo_orden)])
                        if main.tipo_orden == "NPI":
                            get_otd = self.env['dtm.npi'].search([("ot_number","=",main.orden_trabajo)]) # Actualiza el status en los modelos odt y proceso a corte
                        for documento in get_otp.tubos_id:
                            if documento.nombre == self.nombre:
                                get_self = self.env['dtm.tubos.documentos'].search([("id","=",self._origin.id)])
                                if self.cortado:
                                    get_self.write({
                                        "estado": "Material cortado"
                                    })
                                    self.estado = "Material cortado"
                                    documento.cortado = "Material cortado"
                                    get_otd.write({"status":"Corte - Doblado"})
                                    get_otp.write({"status":"cortedoblado"})
                                else:
                                    get_self.write({
                                        "estado": ""
                                    })
                                    self.estado = ""
                                    documento.cortado = ""

class Terminados(models.Model):
    _name = "dtm.tubos.materiales"
    _description = "Se guardan todos los cortes realizados"

    identificador = fields.Integer(string="ID")
    nombre = fields.Char(string="Materiales")
    medida = fields.Char(string="Medidas")
    cantidad = fields.Integer(string="Cantidad")
    inventario = fields.Integer(string="Inventario")
    requerido = fields.Integer(string="Requerido (Compras)")
    localizacion = fields.Char(string="Localización")

class Realizado(models.Model):
    _name = "dtm.tubos.realizados"
    _description = "Modelo para lamacenar todas los cortes de tubos"

    orden_trabajo = fields.Integer(string="Orden de Trabajo", readonly=True)
    fecha_entrada = fields.Date(string="Fecha de entrada", readonly=True)
    nombre_orden = fields.Char(string="Nombre", readonly=True)
    cortadora_id = fields.Many2many("dtm.tubos.documentos", readonly=True)
    tipo_orden = fields.Char(string="Tipo", readonly=True)
    materiales_id = fields.Many2many("dtm.tubos.materiales", string="Materiales", readonly=True)
