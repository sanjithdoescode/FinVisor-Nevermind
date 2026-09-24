/**
 * Mock / demo data for FinVisor 2.0
 * Used as fallback when the backend is not connected.
 */

// ─────────────────────────────────────────────
// Transactions
// ─────────────────────────────────────────────
export const MOCK_TRANSACTIONS = [
  { id: 'TXN-001', date: '2024-09-01T09:15:00Z', description: 'Stripe Payment - Invoice #4821', category: 'Revenue', type: 'CREDIT', amount: 12500.00, balance: 87320.50, anomalous: false },
  { id: 'TXN-002', date: '2024-09-01T10:30:00Z', description: 'AWS Cloud Services', category: 'Infrastructure', type: 'DEBIT', amount: 3842.17, balance: 83478.33, anomalous: false },
  { id: 'TXN-003', date: '2024-09-02T08:00:00Z', description: 'Payroll - September Week 1', category: 'Payroll', type: 'DEBIT', amount: 24000.00, balance: 59478.33, anomalous: false },
  { id: 'TXN-004', date: '2024-09-02T14:22:00Z', description: 'Office Supplies - Amazon Business', category: 'Office', type: 'DEBIT', amount: 842.30, balance: 58636.03, anomalous: false },
  { id: 'TXN-005', date: '2024-09-03T11:05:00Z', description: 'Client Payment - Project Orion', category: 'Revenue', type: 'CREDIT', amount: 35000.00, balance: 93636.03, anomalous: false },
  { id: 'TXN-006', date: '2024-09-03T16:40:00Z', description: 'Zoom Pro - Monthly', category: 'Subscriptions', type: 'DEBIT', amount: 149.90, balance: 93486.13, anomalous: false },
  { id: 'TXN-007', date: '2024-09-04T09:00:00Z', description: 'Slack Business+ - 25 seats', category: 'Subscriptions', type: 'DEBIT', amount: 312.50, balance: 93173.63, anomalous: false },
  { id: 'TXN-008', date: '2024-09-04T13:15:00Z', description: 'UNUSUAL: Crypto Exchange Transfer', category: 'Unknown', type: 'DEBIT', amount: 15000.00, balance: 78173.63, anomalous: true },
  { id: 'TXN-009', date: '2024-09-05T08:30:00Z', description: 'Stripe Payment - Invoice #4835', category: 'Revenue', type: 'CREDIT', amount: 8750.00, balance: 86923.63, anomalous: false },
  { id: 'TXN-010', date: '2024-09-05T10:00:00Z', description: 'Google Workspace - 30 users', category: 'Subscriptions', type: 'DEBIT', amount: 540.00, balance: 86383.63, anomalous: false },
  { id: 'TXN-011', date: '2024-09-06T09:45:00Z', description: 'Electricity Bill - Q3', category: 'Utilities', type: 'DEBIT', amount: 2145.80, balance: 84237.83, anomalous: false },
  { id: 'TXN-012', date: '2024-09-06T14:00:00Z', description: 'Marketing Agency - Ad Spend', category: 'Marketing', type: 'DEBIT', amount: 5000.00, balance: 79237.83, anomalous: false },
  { id: 'TXN-013', date: '2024-09-07T11:30:00Z', description: 'Client Retainer - Acme Corp', category: 'Revenue', type: 'CREDIT', amount: 10000.00, balance: 89237.83, anomalous: false },
  { id: 'TXN-014', date: '2024-09-08T09:00:00Z', description: 'DUPLICATE DETECTED: AWS Cloud Services', category: 'Infrastructure', type: 'DEBIT', amount: 3842.17, balance: 85395.66, anomalous: true },
  { id: 'TXN-015', date: '2024-09-09T10:20:00Z', description: 'Software License - Figma Teams', category: 'Subscriptions', type: 'DEBIT', amount: 225.00, balance: 85170.66, anomalous: false },
  { id: 'TXN-016', date: '2024-09-10T08:00:00Z', description: 'Payroll - September Week 2', category: 'Payroll', type: 'DEBIT', amount: 24000.00, balance: 61170.66, anomalous: false },
  { id: 'TXN-017', date: '2024-09-10T15:00:00Z', description: 'Stripe Payment - Invoice #4856', category: 'Revenue', type: 'CREDIT', amount: 22000.00, balance: 83170.66, anomalous: false },
  { id: 'TXN-018', date: '2024-09-11T09:30:00Z', description: 'Canva Pro - Annual', category: 'Subscriptions', type: 'DEBIT', amount: 119.99, balance: 83050.67, anomalous: false },
  { id: 'TXN-019', date: '2024-09-12T14:45:00Z', description: 'Office Rent - September', category: 'Rent', type: 'DEBIT', amount: 8500.00, balance: 74550.67, anomalous: false },
  { id: 'TXN-020', date: '2024-09-13T10:00:00Z', description: 'WEEKEND ANOMALY: Large Transfer', category: 'Unknown', type: 'DEBIT', amount: 9800.00, balance: 64750.67, anomalous: true },
];

// ─────────────────────────────────────────────
// KPI Summary
// ─────────────────────────────────────────────
export const MOCK_SUMMARY = {
  totalRevenue: 88250.00,
  totalExpenses: 93371.83,
  netCashFlow: -5121.83,
  profitMargin: -5.8,
  revenueChange: 12.4,
  expensesChange: 8.1,
  cashFlowChange: -15.2,
  marginChange: -3.1,
};

// ─────────────────────────────────────────────
// Cash Flow Time Series (30 days)
// ─────────────────────────────────────────────
export const MOCK_CASHFLOW = [
  { date: 'Sep 1', cashflow: 87320, revenue: 12500, expenses: 3842 },
  { date: 'Sep 2', cashflow: 59478, revenue: 0, expenses: 24842 },
  { date: 'Sep 3', cashflow: 93486, revenue: 35000, expenses: 150 },
  { date: 'Sep 4', cashflow: 78174, revenue: 0, expenses: 15313 },
  { date: 'Sep 5', cashflow: 86384, revenue: 8750, expenses: 540 },
  { date: 'Sep 6', cashflow: 79238, revenue: 0, expenses: 7146 },
  { date: 'Sep 7', cashflow: 89238, revenue: 10000, expenses: 0 },
  { date: 'Sep 8', cashflow: 85396, revenue: 0, expenses: 3842 },
  { date: 'Sep 9', cashflow: 85171, revenue: 0, expenses: 225 },
  { date: 'Sep 10', cashflow: 83171, revenue: 22000, expenses: 24000 },
  { date: 'Sep 11', cashflow: 83051, revenue: 0, expenses: 120 },
  { date: 'Sep 12', cashflow: 74551, revenue: 0, expenses: 8500 },
  { date: 'Sep 13', cashflow: 64751, revenue: 0, expenses: 9800 },
  { date: 'Sep 14', cashflow: 72251, revenue: 7500, expenses: 0 },
  { date: 'Sep 15', cashflow: 68751, revenue: 0, expenses: 3500 },
];

// ─────────────────────────────────────────────
// Spending by Category
// ─────────────────────────────────────────────
export const MOCK_SPENDING_BY_CATEGORY = [
  { category: 'Payroll', amount: 48000, color: '#3b82f6' },
  { category: 'Infrastructure', amount: 7684, color: '#8b5cf6' },
  { category: 'Subscriptions', amount: 1347, color: '#06b6d4' },
  { category: 'Rent', amount: 8500, color: '#f59e0b' },
  { category: 'Marketing', amount: 5000, color: '#10b981' },
  { category: 'Utilities', amount: 2146, color: '#ef4444' },
  { category: 'Office', amount: 842, color: '#ec4899' },
  { category: 'Unknown', amount: 24800, color: '#f97316' },
];

// ─────────────────────────────────────────────
// Anomalies
// ─────────────────────────────────────────────
export const MOCK_ANOMALIES = [
  {
    id: 'ANO-001',
    type: 'Unusual Transaction',
    severity: 'critical',
    description: 'Large transfer to Crypto Exchange at unusual hour (04:13 AM)',
    evidence: ['TXN-008'],
    amount: 15000.00,
    date: '2024-09-04T04:13:00Z',
    recommendedAction: 'Verify this transaction immediately with your finance team. Contact bank if unauthorized.',
    acknowledged: false,
  },
  {
    id: 'ANO-002',
    type: 'Duplicate Payment',
    severity: 'high',
    description: 'AWS Cloud Services charged twice within 6 days for identical amount $3,842.17',
    evidence: ['TXN-002', 'TXN-014'],
    amount: 3842.17,
    date: '2024-09-08T09:00:00Z',
    recommendedAction: 'Request a refund from AWS for the duplicate charge. Check if auto-pay settings are misconfigured.',
    acknowledged: false,
  },
  {
    id: 'ANO-003',
    type: 'Weekend Transaction',
    severity: 'medium',
    description: 'Large debit of $9,800 processed on a Saturday to unknown payee',
    evidence: ['TXN-020'],
    amount: 9800.00,
    date: '2024-09-13T10:00:00Z',
    recommendedAction: 'Verify the authorization for this weekend transfer with responsible team member.',
    acknowledged: false,
  },
  {
    id: 'ANO-004',
    type: 'Subscription Creep',
    severity: 'low',
    description: 'Detected 6 active SaaS subscriptions totaling $1,347/month — 3 may be underutilized',
    evidence: ['TXN-006', 'TXN-007', 'TXN-010', 'TXN-015', 'TXN-018'],
    amount: 1347.39,
    date: '2024-09-09T10:20:00Z',
    recommendedAction: 'Audit subscription usage. Consider consolidating tools to reduce monthly SaaS spend.',
    acknowledged: false,
  },
];

// ─────────────────────────────────────────────
// Recurring Costs
// ─────────────────────────────────────────────
export const MOCK_RECURRING_COSTS = [
  { id: 'RC-001', merchant: 'AWS Cloud Services', category: 'Infrastructure', frequency: 'Monthly', amount: 3842.17, annualCost: 46106.04, tag: 'necessary', notes: 'Core infrastructure' },
  { id: 'RC-002', merchant: 'Payroll (25 staff)', category: 'Payroll', frequency: 'Bi-weekly', amount: 24000.00, annualCost: 624000.00, tag: 'necessary', notes: 'Employee compensation' },
  { id: 'RC-003', merchant: 'Office Rent', category: 'Rent', frequency: 'Monthly', amount: 8500.00, annualCost: 102000.00, tag: 'necessary', notes: 'Main office lease' },
  { id: 'RC-004', merchant: 'Google Workspace', category: 'Subscriptions', frequency: 'Monthly', amount: 540.00, annualCost: 6480.00, tag: 'necessary', notes: '30 users @ $18/user' },
  { id: 'RC-005', merchant: 'Slack Business+', category: 'Subscriptions', frequency: 'Monthly', amount: 312.50, annualCost: 3750.00, tag: 'necessary', notes: '25 seats' },
  { id: 'RC-006', merchant: 'Zoom Pro', category: 'Subscriptions', frequency: 'Monthly', amount: 149.90, annualCost: 1798.80, tag: 'suspicious', notes: 'Overlap with Google Meet?' },
  { id: 'RC-007', merchant: 'Figma Teams', category: 'Subscriptions', frequency: 'Monthly', amount: 225.00, annualCost: 2700.00, tag: 'suspicious', notes: 'Only 2 active designers' },
  { id: 'RC-008', merchant: 'Canva Pro', category: 'Subscriptions', frequency: 'Annual', amount: 119.99, annualCost: 119.99, tag: 'suspicious', notes: 'Overlaps with Figma' },
  { id: 'RC-009', merchant: 'Marketing Agency', category: 'Marketing', frequency: 'Monthly', amount: 5000.00, annualCost: 60000.00, tag: 'necessary', notes: 'Digital ad spend' },
  { id: 'RC-010', merchant: 'Electricity Bill', category: 'Utilities', frequency: 'Monthly', amount: 2145.80, annualCost: 25749.60, tag: 'necessary', notes: 'Office utilities' },
];

export const MOCK_RECURRING_SUMMARY = {
  totalMonthlyRecurring: 44835.36,
  totalAnnualRecurring: 872704.43,
  suspiciousMonthly: 495.39,
  hiddenCosts: [
    { name: 'Canva Pro', monthly: 10.00, note: 'Annual plan — easily forgotten' },
    { name: 'Zoom (unused)', monthly: 149.90, note: 'Redundant with Google Meet' },
    { name: 'Figma overseating', monthly: 75.00, note: '3 idle seats @ $25/seat' },
    { name: 'AWS idle resources', monthly: 380.00, note: 'Estimated unused compute' },
  ],
};

// ─────────────────────────────────────────────
// AI Financial Report
// ─────────────────────────────────────────────
export const MOCK_REPORT = {
  generatedAt: '2024-09-13T15:00:00Z',
  overallScore: 62,
  executiveSummary: `FinVisor analysis of your September 2024 financial data reveals a business operating near breakeven with significant cash flow pressure. Your revenue of $88,250 is outpaced by expenses of $93,372, resulting in a net deficit of $5,122 (−5.8% margin). Three critical issues demand immediate attention: a suspicious $15,000 crypto exchange transfer, a duplicate AWS charge of $3,842, and uncontrolled subscription sprawl consuming $1,347/month.`,
  sections: [
    {
      title: '🚨 Critical Findings',
      content: 'A $15,000 transfer to a cryptocurrency exchange was detected at 4:13 AM on September 4th (TXN-008). This transaction exhibits all hallmarks of either fraud or an unauthorized wire — unusual timing, unusual payee category, and no corresponding revenue event. Additionally, AWS charged twice (TXN-002, TXN-014) for $3,842.17 within 6 days — a clear duplicate payment requiring immediate refund request.',
      references: ['TXN-008', 'TXN-002', 'TXN-014'],
    },
    {
      title: '📊 Revenue Analysis',
      content: 'Revenue streams appear healthy with 5 client payments totaling $88,250. Primary sources are project billing (Orion: $35,000), recurring retainers (Acme Corp: $10,000), and Stripe invoicing ($43,250). Revenue is concentrated in 3 clients — increasing client diversification is advised to reduce dependency risk.',
      references: ['TXN-001', 'TXN-005', 'TXN-009', 'TXN-013', 'TXN-017'],
    },
    {
      title: '💸 Expense Optimization',
      content: 'Payroll (51.4% of expenses) and infrastructure are your largest cost centers. SaaS subscription overlap detected: Zoom Pro ($150/mo) appears redundant given Google Workspace includes Meet. Figma Teams has 3 idle seats costing $75/month. Eliminating redundant subscriptions could save ~$500/month ($6,000/year).',
      references: ['TXN-006', 'TXN-007', 'TXN-010', 'TXN-015', 'TXN-018'],
    },
    {
      title: '📈 Cash Flow Forecast',
      content: 'At current burn rate, maintaining operations requires stable revenue of ≥$90,000/month. September\'s shortfall is partly attributable to the anomalous $15,000 transfer. Without this, September would have been near-breakeven at −$1,282. Recommend building a 3-month operating reserve ($280,000) to buffer against revenue volatility.',
      references: [],
    },
  ],
  actionItems: [
    { priority: 1, action: 'Dispute crypto exchange transfer with bank immediately', impact: 'Recover up to $15,000', urgency: 'critical' },
    { priority: 2, action: 'Request AWS refund for duplicate charge TXN-014', impact: 'Recover $3,842', urgency: 'high' },
    { priority: 3, action: 'Cancel Zoom Pro subscription (redundant with Google Meet)', impact: 'Save $1,799/year', urgency: 'medium' },
    { priority: 4, action: 'Audit Figma seats and remove 3 idle licenses', impact: 'Save $900/year', urgency: 'medium' },
    { priority: 5, action: 'Diversify client base to reduce 3-client revenue concentration', impact: 'Reduce business risk', urgency: 'low' },
    { priority: 6, action: 'Build 3-month operating reserve', impact: 'Financial stability', urgency: 'low' },
  ],
};

// ─────────────────────────────────────────────
// What-If Simulator defaults
// ─────────────────────────────────────────────
export const MOCK_SIMULATION_RESULT = {
  scenario: 'Reduce SaaS Subscriptions by 30%',
  currentMonthly: 1347.39,
  projectedMonthly: 943.17,
  monthlySaving: 404.22,
  annualSaving: 4850.64,
  projectedCashflow: [
    { month: 'Month 1', current: -5122, projected: -4718 },
    { month: 'Month 2', current: -5122, projected: -4718 },
    { month: 'Month 3', current: -5122, projected: -4718 },
    { month: 'Month 6', current: -5122, projected: -4718 },
    { month: 'Month 12', current: -5122, projected: -4718 },
  ],
  aiCommentary: 'Reducing SaaS subscriptions by 30% is highly achievable given the identified redundancies (Zoom + Google Meet, Figma idle seats, Canva vs Figma overlap). This change would convert your annual SaaS spend from $16,148 to $11,298, saving $4,850 with no operational impact if managed carefully.',
};
