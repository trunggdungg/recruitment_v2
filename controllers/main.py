from unittest.mock import patch
from odoo import http
from odoo.http import request
from odoo.addons.website_hr_recruitment.controllers.main import WebsiteHrRecruitment


class WebsiteHrRecruitmentSalary(WebsiteHrRecruitment):

    @http.route()
    def jobs(self, page=1, salary_level_id=None, state_id=None, **kwargs):
        salary_level = None
        state = None

        # Lấy salary_level
        if salary_level_id:
            try:
                level = request.env['hr.recruitment.salary.level'].sudo().browse(int(salary_level_id))
                if level.exists():
                    salary_level = level
            except Exception:
                pass

        # Lấy state
        if state_id:
            try:
                state_rec = request.env['res.country.state'].sudo().browse(int(state_id))
                if state_rec.exists():
                    state = state_rec
            except Exception:
                pass

        # Nếu không có filter nào → gọi super bình thường
        if not salary_level and not state:
            response = super().jobs(page=page, **kwargs)
            if hasattr(response, 'qcontext'):
                response.qcontext['salary_level_id'] = None
                response.qcontext['state_id'] = None
            return response

        # Lấy class thực của website object để patch đúng chỗ
        website_class = type(request.website)
        original_search = website_class._search_with_fuzzy
        _salary_level = salary_level
        _state = state

        def patched_search(self_website, search_type, search, limit, order, options):
            total, details, fuzzy = original_search(self_website, search_type, search, limit, order, options)
            if details and details[0].get('results'):
                results = details[0]['results']
                if _salary_level and _state:
                    filtered = results.filtered(
                        lambda j: j.salary_level_id and j.salary_level_id.id == _salary_level.id
                                  and j.state_id and j.state_id.id == _state.id
                    )
                elif _salary_level:
                    filtered = results.filtered(
                        lambda j: j.salary_level_id and j.salary_level_id.id == _salary_level.id
                    )
                elif _state:
                    filtered = results.filtered(
                        lambda j: j.state_id and j.state_id.id == _state.id
                    )
                else:
                    filtered = results
                details[0]['results'] = filtered
                total = len(filtered)
            return total, details, fuzzy

        with patch.object(website_class, '_search_with_fuzzy', patched_search):
            response = super().jobs(page=page, **kwargs)

        if hasattr(response, 'qcontext'):
            response.qcontext['salary_level_id'] = salary_level
            response.qcontext['state_id'] = state

        return response

    @http.route('/hr_recruitment/api/wards', type='http', auth='public', website=True, csrf=False)
    def api_get_wards(self, state_id=None, **kwargs):
        import json
        if not state_id:
            return request.make_response(
                json.dumps({'wards': []}),
                headers=[('Content-Type', 'application/json')]
            )
        try:
            state_id = int(state_id)
        except Exception:
            return request.make_response(
                json.dumps({'wards': []}),
                headers=[('Content-Type', 'application/json')]
            )
        wards = request.env['res.ward'].sudo().search(
            [('state_id', '=', state_id)], order='name'
        )
        data = {'wards': [{'id': w.id, 'name': w.name} for w in wards]}
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )