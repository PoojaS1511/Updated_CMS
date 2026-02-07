/**
 * Payroll Reports Component
 * Generates and displays payroll reports
 */
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import Select from '../../components/common/Select';
import { Alert, AlertDescription } from '../../components/ui/alert';
import { Spinner } from '../../components/ui/spinner';
import { Badge } from '../../components/ui/badge';
import payrollService from '../../services/payrollService';
import {
  FileText,
  Download,
  Calendar,
  DollarSign,
  Users,
  TrendingUp,
  BarChart3,
  PieChart
} from 'lucide-react';

const PayrollReports = () => {
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    month: '',
    year: new Date().getFullYear(),
    department: '',
    reportType: 'summary'
  });

  const reportTypes = [
    { value: 'summary', label: 'Payroll Summary' },
    { value: 'department', label: 'Department-wise Report' },
    { value: 'monthly', label: 'Monthly Comparison' },
    { value: 'deductions', label: 'Deductions Report' }
  ];

  const departments = [
    'CSE', 'ECE', 'Mechanical', 'Civil', 'EEE', 'Administration', 'Accounts'
  ];

  const generateReport = async () => {
    try {
      setLoading(true);
      setError(null);

      // Mock report generation - in real app, this would call an API
      const mockReport = {
        summary: {
          totalEmployees: 45,
          totalPayroll: 2850000,
          averageSalary: 63333,
          totalDeductions: 285000,
          netPayroll: 2565000
        },
        departmentBreakdown: [
          { department: 'CSE', employees: 12, totalSalary: 850000, averageSalary: 70833 },
          { department: 'ECE', employees: 10, totalSalary: 720000, averageSalary: 72000 },
          { department: 'Mechanical', employees: 8, totalSalary: 560000, averageSalary: 70000 },
          { department: 'Administration', employees: 15, totalSalary: 720000, averageSalary: 48000 }
        ],
        monthlyTrend: [
          { month: 'Jan', totalPayroll: 2800000 },
          { month: 'Feb', totalPayroll: 2750000 },
          { month: 'Mar', totalPayroll: 2850000 },
          { month: 'Apr', totalPayroll: 2900000 },
          { month: 'May', totalPayroll: 2850000 }
        ]
      };

      setReportData(mockReport);
    } catch (err) {
      setError('Failed to generate report: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const exportReport = (format) => {
    // Mock export functionality
    alert(`Exporting report as ${format.toUpperCase()}`);
  };

  const formatCurrency = (amount) => {
    return payrollService.formatCurrency(amount);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Payroll Reports</h1>
          <p className="text-gray-600 mt-1">Generate and export payroll reports</p>
        </div>
        <div className="flex items-center space-x-4">
          <Button asChild variant="outline">
            <Link to="/admin/payroll/dashboard">Dashboard</Link>
          </Button>
          <Button asChild variant="outline">
            <Link to="/admin/payroll/list">Payroll List</Link>
          </Button>
        </div>
      </div>

      {/* Report Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Report Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Report Type
              </label>
              <Select
                value={filters.reportType}
                onChange={(e) => setFilters(prev => ({ ...prev, reportType: e.target.value }))}
              >
                {reportTypes.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </Select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Month
              </label>
              <Input
                type="month"
                value={filters.month}
                onChange={(e) => setFilters(prev => ({ ...prev, month: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Year
              </label>
              <Input
                type="number"
                value={filters.year}
                onChange={(e) => setFilters(prev => ({ ...prev, year: e.target.value }))}
                min="2020"
                max="2030"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Department
              </label>
              <Select
                value={filters.department}
                onChange={(e) => setFilters(prev => ({ ...prev, department: e.target.value }))}
              >
                <option value="">All Departments</option>
                {departments.map(dept => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </Select>
            </div>
          </div>
          <div className="mt-4 flex gap-4">
            <Button onClick={generateReport} disabled={loading}>
              {loading ? <Spinner size="sm" className="mr-2" /> : <BarChart3 className="h-4 w-4 mr-2" />}
              Generate Report
            </Button>
            {reportData && (
              <>
                <Button variant="outline" onClick={() => exportReport('pdf')}>
                  <Download className="h-4 w-4 mr-2" />
                  Export PDF
                </Button>
                <Button variant="outline" onClick={() => exportReport('excel')}>
                  <Download className="h-4 w-4 mr-2" />
                  Export Excel
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert variant="danger">
          {error}
        </Alert>
      )}

      {/* Report Results */}
      {reportData && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Employees</p>
                    <p className="text-2xl font-bold text-blue-600">{reportData.summary.totalEmployees}</p>
                  </div>
                  <Users className="h-8 w-8 text-blue-500" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Payroll</p>
                    <p className="text-2xl font-bold text-green-600">{formatCurrency(reportData.summary.totalPayroll)}</p>
                  </div>
                  <DollarSign className="h-8 w-8 text-green-500" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Average Salary</p>
                    <p className="text-2xl font-bold text-purple-600">{formatCurrency(reportData.summary.averageSalary)}</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-purple-500" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Total Deductions</p>
                    <p className="text-2xl font-bold text-red-600">{formatCurrency(reportData.summary.totalDeductions)}</p>
                  </div>
                  <TrendingUp className="h-8 w-8 text-red-500" />
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-600">Net Payroll</p>
                    <p className="text-2xl font-bold text-indigo-600">{formatCurrency(reportData.summary.netPayroll)}</p>
                  </div>
                  <DollarSign className="h-8 w-8 text-indigo-500" />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Department Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Department-wise Breakdown</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Department
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Employees
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Total Salary
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Average Salary
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {reportData.departmentBreakdown.map((dept, index) => (
                      <tr key={index}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {dept.department}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {dept.employees}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatCurrency(dept.totalSalary)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatCurrency(dept.averageSalary)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Monthly Trend */}
          <Card>
            <CardHeader>
              <CardTitle>Monthly Payroll Trend</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Month
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Total Payroll
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {reportData.monthlyTrend.map((month, index) => (
                      <tr key={index}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {month.month}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatCurrency(month.totalPayroll)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Empty State */}
      {!reportData && !loading && (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <FileText className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No Report Generated</h3>
              <p className="text-gray-500 mb-4">
                Configure your report parameters and click "Generate Report" to create a payroll report.
              </p>
              <Button onClick={generateReport}>
                Generate Sample Report
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default PayrollReports;
