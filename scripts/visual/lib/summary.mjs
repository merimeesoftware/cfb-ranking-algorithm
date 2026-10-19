function cell(value) {
  return String(value ?? '').replace(/\|/g, '\\|').replace(/\n/g, ' ');
}

function pct(ratio) {
  if (typeof ratio !== 'number') return '';
  return `${(ratio * 100).toFixed(3)}%`;
}

/**
 * Job summary. Routes with no signed comp are `no comps`, and a run that
 * never compared a signed comp says so in the headline. That headline is
 * not a pass.
 */
export function buildSummary(report) {
  const results = report.results || [];
  const violations = report.violations || [];
  const compared = results.filter((row) => row.status === 'pass' || row.status === 'fail');
  const failures = results.filter((row) => row.status === 'fail');
  let headline;
  if (report.httpError) {
    headline = `Preview stills failed: ${report.httpError}`;
  } else if (failures.length > 0 || violations.length > 0 || report.agentHits > 0) {
    headline = 'Preview stills failed.';
  } else if (results.length > 0 && compared.length === 0) {
    headline = 'Preview stills: no comps. This run is not a pass.';
  } else if (compared.some((row) => row.status === 'pass')) {
    const noComps = results.filter((row) => row.status === 'no comps').length;
    headline = `Preview stills: ${compared.filter((row) => row.status === 'pass').length} signed comp(s) matched.`;
    if (noComps > 0) {
      headline += ` ${noComps} route(s) are no comps (not a pass).`;
    }
  } else {
    headline = 'Preview stills: nothing captured. This run is not a pass.';
  }

  const lines = [
    `## ${headline}`,
    '',
    `Chrome \`${report.chrome || 'unknown'}\`. pixelmatch threshold \`${report.pixelmatchThreshold}\`, max diff ratio \`${report.maxDiffRatio}\`.`,
    '',
    '| Route | Width | Result | Detail |',
    '| --- | --- | --- | --- |',
  ];
  if (results.length === 0) {
    lines.push('| — | — | no comps | no routes captured |');
  }
  for (const row of results) {
    const detail =
      row.status === 'fail' && typeof row.ratio === 'number'
        ? `${row.reason}; ${row.diffPixels} px (${pct(row.ratio)})`
        : row.reason || '';
    lines.push(
      `| ${cell(row.route)} | ${cell(row.width)} | ${cell(row.status)} | ${cell(detail)} |`
    );
  }
  if (violations.length > 0) {
    lines.push('', '### Request guard', '');
    lines.push('| Kind | Method | URL |');
    lines.push('| --- | --- | --- |');
    for (const hit of violations) {
      lines.push(`| ${cell(hit.kind)} | ${cell(hit.method)} | ${cell(hit.url)} |`);
    }
  }
  if (report.agentHits > 0) {
    lines.push('', `Fixture server saw ${report.agentHits} request(s) to \`/api/agent/*\`.`);
  }
  lines.push('');
  return lines.join('\n');
}

export function resultStatus(row) {
  if (row.status === 'pass' || row.status === 'fail' || row.status === 'no comps') {
    return row.status;
  }
  throw new Error(`unexpected stills status: ${row.status}`);
}
