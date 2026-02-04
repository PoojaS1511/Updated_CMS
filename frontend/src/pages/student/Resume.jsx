import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import axios from 'axios';
import { 
  DocumentTextIcon, 
  ArrowUpTrayIcon, 
  DocumentMagnifyingGlassIcon,
  CheckCircleIcon,
  XCircleIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';
import apiService from '../../services/api';
import { API_URL } from '../../config';

const Resume = () => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [hasResume, setHasResume] = useState(false);
  const [resumeUrl, setResumeUrl] = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const studentId = JSON.parse(localStorage.getItem('user') || '{}').user_id;
  const navigate = useNavigate();

  useEffect(() => {
    const checkExistingResume = async () => {
      try {
        const response = await apiService.getStudentResume(studentId);
        if (response.uploaded) {
          setHasResume(true);
          setResumeUrl(response.data?.resume_url || '');
          setAnalysis(response.data?.analysis || 'Resume found. You can upload a new one to replace it.');
        } else {
          setAnalysis('No resume found. Please upload your resume.');
        }
      } catch (error) {
        console.error('Error checking for existing resume:', error);
        if (error.response?.status !== 404) {
          toast.error('Failed to check for existing resume');
        }
      }
    };

    if (studentId) {
      checkExistingResume();
    }
  }, [studentId]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      toast.error('Please select a file first');
      return;
    }

    setIsUploading(true);
    setIsAnalyzing(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('student_id', studentId);

      // Reset progress
      setUploadProgress(0);
      setAnalysisProgress(0);
      
      // Start progress simulation
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          const newProgress = prev + Math.floor(Math.random() * 15);
          return newProgress > 90 ? 90 : newProgress;
        });
      }, 300);

      console.log('Uploading resume with:', {
        studentId,
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type
      });

      const response = await axios({
        method: 'post',
        url: `${API_URL}/resume/upload`,
        data: formData,
        withCredentials: true,
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted > 90 ? 90 : percentCompleted);
        },
        headers: {
          'Content-Type': 'multipart/form-data',
          'Accept': 'application/json',
        },
      });
      
      // Clear upload progress interval
      clearInterval(progressInterval);
      setUploadProgress(100);
      
      // Simulate analysis progress
      const analysisInterval = setInterval(() => {
        setAnalysisProgress(prev => {
          const newProgress = prev + Math.floor(Math.random() * 10);
          if (newProgress >= 100) {
            clearInterval(analysisInterval);
            return 100;
          }
          return newProgress;
        });
      }, 300);
      
      if (response.data?.success) {
        // Complete the analysis progress
        setAnalysisProgress(100);
        setTimeout(() => {
          setHasResume(true);
          setResumeUrl(response.data.data?.resume_url || '');
          setAnalysis({
            score: response.data.data?.analysis?.score || 0,
            strengths: response.data.data?.analysis?.strengths || [],
            recommendations: response.data.data?.analysis?.recommendations || [],
            skills: response.data.data?.analysis?.skills_identified || []
          });
          toast.success('Resume analyzed successfully');
        }, 500);
      } else {
        throw new Error(response.data?.error || 'Failed to analyze resume');
      }
    } catch (error) {
      console.error('Error uploading resume:', error);
      toast.error(error.response?.data?.error || error.message || 'Failed to upload resume');
    } finally {
      setIsUploading(false);
    }
  };

  const handleViewResume = () => {
    if (resumeUrl) {
      window.open(resumeUrl, '_blank');
    }
  };

  const renderAnalysis = () => {
    if (!analysis) return null;

    return (
      <div className="mt-8 space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Resume Analysis</h2>
          
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">ATS Score</span>
              <span className={`text-lg font-bold ${
                analysis.score >= 70 ? 'text-green-600' : 
                analysis.score >= 40 ? 'text-yellow-600' : 'text-red-600'
              }`}>
                {analysis.score}/100
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div 
                className={`h-2.5 rounded-full ${
                  analysis.score >= 70 ? 'bg-green-500' : 
                  analysis.score >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                }`} 
                style={{ width: `${analysis.score}%` }}
              ></div>
            </div>
          </div>

          {analysis.strengths.length > 0 && (
            <div className="mb-6">
              <h3 className="text-md font-medium text-gray-800 mb-2 flex items-center">
                <CheckCircleIcon className="h-5 w-5 text-green-500 mr-2" />
                Key Strengths
              </h3>
              <ul className="list-disc pl-5 space-y-1">
                {analysis.strengths.map((strength, index) => (
                  <li key={index} className="text-gray-700">{strength}</li>
                ))}
              </ul>
            </div>
          )}

          {analysis.skills.length > 0 && (
            <div className="mb-6">
              <h3 className="text-md font-medium text-gray-800 mb-2">
                <InformationCircleIcon className="h-5 w-5 text-blue-500 mr-2 inline" />
                Skills Identified
              </h3>
              <div className="flex flex-wrap gap-2">
                {analysis.skills.map((skill, index) => (
                  <span key={index} className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          {analysis.recommendations.length > 0 && (
            <div>
              <h3 className="text-md font-medium text-gray-800 mb-2 flex items-center">
                <XCircleIcon className="h-5 w-5 text-red-500 mr-2" />
                Recommendations for Improvement
              </h3>
              <ul className="list-disc pl-5 space-y-2">
                {analysis.recommendations.map((rec, index) => (
                  <li key={index} className="text-gray-700">{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    );
  };

  const renderProgressBar = (progress, label, color = 'bg-royal-600') => (
    <div className="w-full mb-2">
      <div className="flex justify-between text-sm text-gray-600 mb-1">
        <span>{label}</span>
        <span>{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div 
          className={`h-2.5 rounded-full ${color}`} 
          style={{ width: `${progress}%`, transition: 'width 0.3s ease' }}
        ></div>
      </div>
    </div>
  );

  return (
    <div className="p-6">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center">
              <DocumentTextIcon className="h-8 w-8 text-royal-600 mr-2" />
              <h1 className="text-2xl font-bold text-gray-800">My Resume</h1>
            </div>
            {analysis && (
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                analysis.score >= 70 ? 'bg-green-100 text-green-800' : 
                analysis.score >= 40 ? 'bg-yellow-100 text-yellow-800' : 'bg-red-100 text-red-800'
              }`}>
                ATS Score: {analysis.score}/100
              </div>
            )}
          </div>
          
          {isAnalyzing && !analysis && (
            <div className="mb-6 p-4 bg-blue-50 rounded-lg">
              <h3 className="text-lg font-medium text-blue-800 mb-3">Processing Your Resume</h3>
              
              {uploadProgress < 100 && (
                <div className="mb-4">
                  <p className="text-sm text-blue-700 mb-2">Uploading file...</p>
                  {renderProgressBar(uploadProgress, 'Upload Progress', 'bg-blue-500')}
                </div>
              )}
              
              {uploadProgress === 100 && analysisProgress < 100 && (
                <div>
                  <p className="text-sm text-blue-700 mb-2">Analyzing content...</p>
                  {renderProgressBar(analysisProgress, 'Analysis Progress', 'bg-green-500')}
                  <p className="text-xs text-gray-500 mt-2">This may take a moment. Please don't close this page.</p>
                </div>
              )}
              
              {(uploadProgress < 100 || analysisProgress < 100) && (
                <div className="flex items-center mt-3">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span className="text-sm text-blue-700">
                    {uploadProgress < 100 ? 'Uploading...' : 'Analyzing...'}
                  </span>
                </div>
              )}
            </div>
          )}

          {hasResume && (
            <div className="mb-6">
              <button
                onClick={handleViewResume}
                className="flex items-center px-4 py-2 bg-royal-100 text-royal-700 rounded-md hover:bg-royal-200 transition-colors"
              >
                <DocumentMagnifyingGlassIcon className="h-5 w-5 mr-2" />
                View Current Resume
              </button>
            </div>
          )}

          <div 
            className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-royal-500 transition-colors duration-200 cursor-pointer"
            onClick={() => document.getElementById('resume-upload').click()}
          >
            <div className="flex flex-col items-center justify-center space-y-4">
              <ArrowUpTrayIcon className="h-12 w-12 text-royal-500" />
              <div className="text-sm text-gray-600">
                {file ? (
                  <p className="font-medium text-royal-700">Selected file: {file.name}</p>
                ) : (
                  <p>Drag and drop your resume here, or <span className="text-royal-600 font-medium">click to select</span></p>
                )}
              </div>
              <div className="space-y-4">
                <div>
                  <label 
                    htmlFor="resume-upload"
                    className="cursor-pointer bg-royal-600 text-white px-6 py-2.5 rounded-md hover:bg-royal-700 transition-colors inline-block text-sm font-medium shadow-sm"
                  >
                    {file ? 'Change File' : 'Select File'}
                  </label>
                  <input
                    id="resume-upload"
                    type="file"
                    className="hidden"
                    accept=".pdf,.doc,.docx,.txt"
                    onChange={handleFileChange}
                  />
                </div>
                {file && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleUpload();
                    }}
                    disabled={isUploading}
                    className={`px-6 py-2.5 rounded-md text-white text-sm font-medium shadow-sm ${
                      isUploading 
                        ? 'bg-gray-400 cursor-not-allowed' 
                        : 'bg-green-600 hover:bg-green-700 hover:shadow-md'
                    } transition-all`}
                  >
                    {isUploading ? 'Uploading...' : 'Upload Resume'}
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="mt-6 text-sm text-gray-500">
            <p className="text-sm text-gray-600">
              <span className="font-medium">Accepted file types:</span> .pdf, .doc, .docx, .txt
              <br />
              <span className="font-medium">Maximum file size:</span> 5MB
            </p>
          </div>
          
          {analysis && renderAnalysis()}
          
          <div className="mt-8 p-4 bg-blue-50 rounded-lg">
            <h3 className="text-lg font-medium text-blue-800 mb-2">Resume Tips</h3>
            <ul className="list-disc pl-5 space-y-1 text-sm text-blue-700">
              <li>Use clear section headings (Education, Experience, Skills)</li>
              <li>Include relevant keywords from the job description</li>
              <li>Quantify your achievements with numbers where possible</li>
              <li>Keep it concise (1-2 pages for most candidates)</li>
              <li>Use a clean, professional format</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Resume;
