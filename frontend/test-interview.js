// Manual test script for interview question generation
const axios = require('axios');

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Test data for different interview types
const testCases = [
  {
    name: 'General Interview',
    data: {
      job_title: 'Software Engineer',
      job_description: 'We are looking for a software engineer with 3+ years of experience in JavaScript, React, and Node.js.',
      interview_type: 'general',
      duration: 30,
      cv_text: 'Experienced software engineer with 5 years of experience in web development using JavaScript, React, and Node.js.'
    }
  },
  {
    name: 'Technical Interview',
    data: {
      job_title: 'Senior Frontend Developer',
      job_description: 'Looking for a senior frontend developer with expertise in React, TypeScript, and modern web technologies.',
      interview_type: 'technical',
      duration: 45,
      cv_text: 'Senior developer with 7 years of experience in frontend development, specializing in React, TypeScript, and Redux.'
    }
  },
  {
    name: 'Behavioral Interview',
    data: {
      job_title: 'Product Manager',
      job_description: 'Seeking a product manager to lead our product development team and drive product strategy.',
      interview_type: 'behavioral',
      duration: 30,
      cv_text: 'Product manager with experience in agile methodologies, user research, and product roadmap development.'
    }
  },
  {
    name: 'Case Study Interview',
    data: {
      job_title: 'Business Analyst',
      job_description: 'Looking for a business analyst to help identify business needs and develop solutions.',
      interview_type: 'case_study',
      duration: 60,
      cv_text: 'Business analyst with experience in data analysis, process improvement, and stakeholder management.'
    }
  }
];

// Function to test interview question generation
async function testInterviewGeneration(testCase) {
  console.log(`\n🧪 Testing: ${testCase.name}`);
  console.log('--------------------------------------------------');
  
  try {
    console.log('Sending request...');
    const response = await axios.post(
      `${API_BASE_URL}/api/generate-interview`,
      testCase.data,
      {
        headers: {
          'Content-Type': 'application/json',
          // Note: In a real test, you would include authentication
          // 'Authorization': `Bearer ${token}`
        }
      }
    );
    
    if (response.data && response.data.questions && response.data.questions.length > 0) {
      console.log('✅ Success! Questions generated:');
      console.log(`   Number of questions: ${response.data.questions.length}`);
      console.log('   Sample questions:');
      response.data.questions.slice(0, 3).forEach((q, i) => {
        console.log(`   ${i+1}. ${q.text || q.question}`);
      });
      return true;
    } else {
      console.log('❌ Failed: No questions returned');
      console.log(response.data);
      return false;
    }
  } catch (error) {
    console.log('❌ Error:');
    if (error.response) {
      console.log(`   Status: ${error.response.status}`);
      console.log(`   Message: ${JSON.stringify(error.response.data)}`);
    } else {
      console.log(`   ${error.message}`);
    }
    return false;
  }
}

// Run all tests
async function runAllTests() {
  console.log('🚀 Starting Interview Generation Tests');
  console.log('==================================================');
  
  let passedTests = 0;
  
  for (const testCase of testCases) {
    const passed = await testInterviewGeneration(testCase);
    if (passed) passedTests++;
  }
  
  console.log('\n==================================================');
  console.log(`📊 Test Results: ${passedTests}/${testCases.length} tests passed`);
  
  if (passedTests === testCases.length) {
    console.log('🎉 All tests passed!');
  } else {
    console.log('⚠️ Some tests failed. Check the logs above for details.');
  }
}

// Run the tests
runAllTests().catch(err => {
  console.error('Error running tests:', err);
}); 