document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('rankingForm');
    const updateBtn = document.getElementById('updateBtn');
    
    // Initial load
    fetchRankings();

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        fetchRankings();
    });

    // Update range value displays for weight sliders
    ['tq', 'rec', 'conf'].forEach(key => {
        const input = document.getElementById(key + '_weight');
        const display = document.getElementById(key + '_val');
        if(input && display) {
            input.addEventListener('input', e => display.textContent = Math.round(e.target.value * 100));
        }
    });
    
    // Prior strength slider (special handling for dual display)
    const priorInput = document.getElementById('prior_strength');
    const priorDisplay = document.getElementById('prior_val');
    const freshDisplay = document.getElementById('fresh_val');
    if(priorInput && priorDisplay && freshDisplay) {
        priorInput.addEventListener('input', e => {
            const val = Math.round(e.target.value * 100);
            priorDisplay.textContent = val;
            freshDisplay.textContent = 100 - val;
        });
    }

    function fetchRankings() {
        // Show loading
        setLoadingState();
        
        // Build query string
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        
        // Fetch
        fetch(`/rankings?${params.toString()}`, {
            headers: {
                'Accept': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            renderTeamTable(data.team_rankings);
            renderConfTable(data.conference_rankings);
            updateLinks(params);
        })
        .catch(error => {
            console.error('Error:', error);
            showError();
        });
    }

    function setLoadingState() {
        const spinner = `<tr><td colspan="8" class="text-center py-4"><div class="spinner-border text-primary" role="status"></div><div class="mt-2">Calculating rankings...</div></td></tr>`;
        document.getElementById('teamTableBody').innerHTML = spinner;
        document.getElementById('confTableBody').innerHTML = spinner;
        updateBtn.disabled = true;
        updateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';
    }

    function renderTeamTable(teams) {
        const tbody = document.getElementById('teamTableBody');
        tbody.innerHTML = '';
        
        // Top 25 only
        const top25 = teams.slice(0, 25);
        
        top25.forEach((team, index) => {
            const row = document.createElement('tr');
            row.style.cursor = 'pointer';
            row.classList.add('team-row');
            row.dataset.teamName = team.team_name;
            row.innerHTML = `
                    <td class="ps-3 fw-bold">${index + 1}</td>
                    <td>
                        <div class="fw-bold text-primary">${team.team_name}</div>
                    </td>
                    <td><span class="badge bg-light text-dark border">${team.conference}</span></td>
                    <td>${team.records.total_wins}-${team.records.total_losses}</td>
                    <td class="text-center">${team.team_quality_score.toFixed(2)}</td>
                    <td class="text-center">${team.record_score.toFixed(2)}</td>
                    <td class="text-center">${team.conference_quality_score.toFixed(2)}</td>
                    <td class="text-end pe-3 fw-bold">${team.final_ranking_score.toFixed(2)}</td>
            `;
            row.addEventListener('click', () => showTeamBreakdown(team.team_name));
            tbody.appendChild(row);
        });
        
        updateBtn.disabled = false;
        updateBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update Rankings';
    }
    
    function showTeamBreakdown(teamName) {
        // Build query string with current form params
        const formData = new FormData(form);
        const params = new URLSearchParams(formData);
        
        // Show loading modal
        const modal = new bootstrap.Modal(document.getElementById('teamBreakdownModal'));
        document.getElementById('teamBreakdownContent').innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <div class="mt-2">Loading breakdown for ${teamName}...</div>
            </div>
        `;
        modal.show();
        
        // Fetch team breakdown
        fetch(`/rankings/team/${encodeURIComponent(teamName)}?${params.toString()}`, {
            headers: { 'Accept': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                document.getElementById('teamBreakdownContent').innerHTML = `
                    <div class="alert alert-danger">${data.error}</div>
                `;
                return;
            }
            renderTeamBreakdown(data);
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('teamBreakdownContent').innerHTML = `
                <div class="alert alert-danger">Error loading team breakdown. Please try again.</div>
            `;
        });
    }
    
    function renderTeamBreakdown(data) {
        const team = data.team;
        const formula = data.formula_breakdown;
        
        let html = `
            <div class="row mb-4">
                <div class="col-md-6">
                    <h4 class="mb-3">
                        <span class="badge bg-primary me-2">#${team.rank}</span>
                        ${team.name}
                    </h4>
                    <p class="text-muted mb-2">
                        <span class="badge bg-secondary">${team.conference}</span>
                        <strong class="ms-2">${team.record}</strong> (${team.conf_record} conf)
                    </p>
                    <p class="small text-muted">
                        vs P4: ${team.power_record} | vs G5: ${team.g5_record}
                    </p>
                </div>
                <div class="col-md-6">
                    <div class="card bg-light">
                        <div class="card-body py-2">
                            <h6 class="card-title mb-2">Final Score Breakdown</h6>
                            <div class="small">
                                <div class="d-flex justify-content-between">
                                    <span>Team Quality (55%):</span>
                                    <strong>${team.team_quality.toFixed(1)} × 0.55 = ${formula.tq_contribution.toFixed(1)}</strong>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <span>Record Score (35%):</span>
                                    <strong>${team.record_score.toFixed(1)} × 0.35 = ${formula.rec_contribution.toFixed(1)}</strong>
                                </div>
                                <div class="d-flex justify-content-between">
                                    <span>Conf Quality (10%):</span>
                                    <strong>${team.conference_quality.toFixed(1)} × 0.10 = ${formula.cq_contribution.toFixed(1)}</strong>
                                </div>
                                <hr class="my-1">
                                <div class="d-flex justify-content-between fw-bold">
                                    <span>Final Score:</span>
                                    <span>${formula.total.toFixed(2)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row mb-3">
                <div class="col-md-6">
                    <div class="small">
                        <strong>SoS (Avg Opp Elo):</strong> ${team.sos.toFixed(0)}
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="small">
                        <strong>SoV (Avg Win Opp Elo):</strong> ${team.sov.toFixed(0)}
                    </div>
                </div>
            </div>
        `;
        
        // Teams ahead comparison
        if (data.comparisons_ahead.length > 0) {
            html += `
                <h5 class="mt-4 mb-3"><i class="fas fa-arrow-up text-success me-2"></i>Why Behind These Teams</h5>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered">
                        <thead class="table-light">
                            <tr>
                                <th>Rank</th>
                                <th>Team</th>
                                <th>Gap</th>
                                <th>Key Factors</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            data.comparisons_ahead.forEach(comp => {
                const factors = comp.factors.slice(0, 2).map(f => {
                    const icon = f.advantage === 'other' ? '↑' : '↓';
                    const color = f.advantage === 'other' ? 'text-danger' : 'text-success';
                    return `<span class="${color}">${icon} ${f.factor}</span>: ${f.explanation}`;
                }).join('<br>');
                
                html += `
                    <tr>
                        <td class="fw-bold">#${comp.other_rank}</td>
                        <td>${comp.other_team} <small class="text-muted">(${comp.other_record})</small></td>
                        <td class="text-danger">${comp.score_diff.toFixed(1)}</td>
                        <td class="small">${factors || 'Marginal differences'}</td>
                    </tr>
                `;
            });
            
            html += `</tbody></table></div>`;
        }
        
        // Teams behind comparison
        if (data.comparisons_behind.length > 0) {
            html += `
                <h5 class="mt-4 mb-3"><i class="fas fa-arrow-down text-danger me-2"></i>Why Ahead of These Teams</h5>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered">
                        <thead class="table-light">
                            <tr>
                                <th>Rank</th>
                                <th>Team</th>
                                <th>Gap</th>
                                <th>Key Factors</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            data.comparisons_behind.forEach(comp => {
                const factors = comp.factors.slice(0, 2).map(f => {
                    const icon = f.advantage === 'target' ? '↑' : '↓';
                    const color = f.advantage === 'target' ? 'text-success' : 'text-danger';
                    return `<span class="${color}">${icon} ${f.factor}</span>: ${f.explanation}`;
                }).join('<br>');
                
                html += `
                    <tr>
                        <td class="fw-bold">#${comp.other_rank}</td>
                        <td>${comp.other_team} <small class="text-muted">(${comp.other_record})</small></td>
                        <td class="text-success">+${comp.score_diff.toFixed(1)}</td>
                        <td class="small">${factors || 'Marginal differences'}</td>
                    </tr>
                `;
            });
            
            html += `</tbody></table></div>`;
        }
        
        document.getElementById('teamBreakdownContent').innerHTML = html;
    }

    function renderConfTable(confs) {
        const tbody = document.getElementById('confTableBody');
        tbody.innerHTML = '';
        
        // Top 7 only (usually P4 + top G5s)
        const top7 = confs.slice(0, 7);
        
        top7.forEach((conf, index) => {
            const row = `
                <tr>
                    <td class="ps-3 fw-bold">${index + 1}</td>
                    <td>${conf.conference_name}</td>
                    <td class="text-center">${conf.number_of_teams}</td>
                    <td class="text-center">${conf.record_vs_p4}</td>
                    <td class="text-center">${conf.record_vs_g5}</td>
                    <td class="text-end pe-3 fw-bold">${conf.average_team_quality.toFixed(2)}</td>
                </tr>
            `;
            tbody.innerHTML += row;
        });
    }

    function updateLinks(params) {
        const qs = params.toString();
        document.getElementById('seeMoreTeams').href = `/rankings/full?${qs}`;
        document.getElementById('seeMoreConfs').href = `/rankings/full?${qs}&tab=confs`;
    }

    function showError() {
        const err = `<tr><td colspan="7" class="text-center text-danger py-4"><i class="fas fa-exclamation-triangle"></i> Error loading rankings. Please try again.</td></tr>`;
        document.getElementById('teamTableBody').innerHTML = err;
        document.getElementById('confTableBody').innerHTML = err;
        updateBtn.disabled = false;
        updateBtn.innerHTML = 'Retry';
    }
});