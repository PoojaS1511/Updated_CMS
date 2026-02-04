import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';
import { toast } from 'react-toastify';

const MyResearchPapers = () => {
  const { user } = useAuth();
  const [researchPapers, setResearchPapers] = useState([]);
  const [faculty, setFaculty] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchFacultyAndResearchPapers = async () => {
      try {
        setLoading(true);
        
        // Fetch faculty details
        const { data: facultyData, error: facultyError } = await supabase
          .from('faculties')
          .select('*')
          .eq('id', user.id)
          .single();

        if (facultyError) throw facultyError;
        setFaculty(facultyData);

        // Fetch research papers for the faculty
        const { data: papersData, error: papersError } = await supabase
          .from('research_papers')
          .select('*')
          .eq('faculty_id', facultyData.id)
          .order('publication_date', { ascending: false });

        if (papersError) throw papersError;
        setResearchPapers(papersData || []);
      } catch (err) {
        console.error('Error:', err);
        setError('Failed to load data');
        toast.error('Failed to load research papers');
      } finally {
        setLoading(false);
      }
    };

    if (user?.id) {
      fetchFacultyAndResearchPapers();
    }
  }, [user]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-l-4 border-red-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">My Research Papers</h1>
      </div>

      <div className="mb-6 bg-white p-4 rounded-lg shadow">
        <h2 className="text-lg font-semibold mb-2">Faculty Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-gray-500">Name</p>
            <p className="font-medium">{faculty?.full_name || 'N/A'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Employee ID</p>
            <p className="font-medium">{faculty?.employee_id || 'N/A'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Department</p>
            <p className="font-medium">{faculty?.department_id || 'N/A'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Designation</p>
            <p className="font-medium">{faculty?.designation || 'N/A'}</p>
          </div>
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-lg">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Journal/Conference
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Published
                </th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {researchPapers.length > 0 ? (
                researchPapers.map((paper) => (
                  <tr key={paper.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900">{paper.title}</div>
                      <div className="text-sm text-gray-500">{paper.authors}</div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">{paper.journal || paper.conference}</div>
                      {paper.volume_issue && (
                        <div className="text-sm text-gray-500">{paper.volume_issue}</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">
                        {paper.publication_date ? new Date(paper.publication_date).toLocaleDateString() : 'N/A'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                      {paper.pdf_url && (
                        <a
                          href={paper.pdf_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          View PDF
                        </a>
                      )}
                      {paper.doi && (
                        <a
                          href={`https://doi.org/${paper.doi}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-2 text-indigo-600 hover:text-indigo-900"
                        >
                          DOI
                        </a>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="px-6 py-4 text-center text-sm text-gray-500">
                    No research papers found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default MyResearchPapers;
