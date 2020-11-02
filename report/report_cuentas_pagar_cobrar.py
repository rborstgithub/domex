# -*- coding: utf-8 -*-

import datetime
import time
from datetime import date
from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import logging
# import odoo.addons.l10n_gt_extra.a_letras

class ReportCuentasPagarCobrar(models.AbstractModel):
    _inherit = "report.account.report_partnerledger"
    _name = 'report.domex.cuentas_pagar_cobrar'
    
    def fecha_impresion(self):
        fecha = str(datetime.datetime.strptime(str(date.today()), '%Y-%m-%d').date())
        return fecha
   
    @api.model
    def render_html(self, docids, data=None):
        if not data.get('form'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        data['computed'] = {}

        obj_partner = self.env['res.partner']
        query_get_data = self.env['account.move.line'].with_context(data['form'].get('used_context', {}))._query_get()
        data['computed']['move_state'] = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            data['computed']['move_state'] = ['posted']
        result_selection = data['form'].get('result_selection', 'customer')
        if result_selection == 'supplier':
            data['computed']['ACCOUNT_TYPE'] = ['payable']
            data['computed']['tipo'] = 1
        elif result_selection == 'customer':
            data['computed']['ACCOUNT_TYPE'] = ['receivable']
            data['computed']['tipo'] = 2
        else:
            data['computed']['ACCOUNT_TYPE'] = ['payable', 'receivable']
            data['computed']['tipo'] = 3
            

        self.env.cr.execute("""
            SELECT a.id
            FROM account_account a
            WHERE a.internal_type IN %s
            AND NOT a.deprecated""", (tuple(data['computed']['ACCOUNT_TYPE']),))
        data['computed']['account_ids'] = [a for (a,) in self.env.cr.fetchall()]
        params = [tuple(data['computed']['move_state']), tuple(data['computed']['account_ids'])] + query_get_data[2]
        reconcile_clause = "" if data['form']['reconciled'] else ' AND "account_move_line".full_reconcile_id IS NULL '
        query = """
            SELECT DISTINCT "account_move_line".partner_id
            FROM """ + query_get_data[0] + """, account_account AS account, account_move AS am
            WHERE "account_move_line".partner_id IS NOT NULL
                AND "account_move_line".account_id = account.id
                AND am.id = "account_move_line".move_id
                AND am.state IN %s
                AND "account_move_line".account_id IN %s
                AND NOT account.deprecated
                AND """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))
        partner_ids = [res['partner_id'] for res in self.env.cr.dictfetchall()]
        partners = obj_partner.browse(partner_ids)
        partners = sorted(partners, key=lambda x: (x.ref, x.name))
        docargs = {
            'doc_ids': partner_ids,
            'doc_model': self.env['res.partner'],
            'data': data,
            'docs': partners,
            'time': time,
            'lines': self._lines,
            'sum_partner': self._sum_partner,
            'fecha_impresion': self.fecha_impresion,
        }
        return self.env['report'].render('domex.cuentas_pagar_cobrar', docargs)
    