# AI Interview Prep Frontend

This is the frontend application for the AI Interview Preparation platform. It provides a user interface for setting up and participating in AI-powered interviews, as well as viewing evaluation results.

## Features

- Modern, responsive UI built with Next.js and Tailwind CSS
- Interactive interview setup with job details and CV upload
- Live video interview experience with WebRTC
- Code editor for technical interview questions
- Detailed evaluation and feedback display

## Tech Stack

- Next.js 14
- React 18
- Tailwind CSS
- Monaco Editor (for code challenges)
- WebRTC (for video communication)

## Getting Started

First, install the dependencies:

```bash
npm install
# or
yarn install
```

Then, run the development server:

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Project Structure

- `app/` - Next.js app directory
  - `page.tsx` - Homepage
  - `layout.tsx` - Root layout with header and footer
  - `interview/` - Interview-related pages
    - `setup/` - Interview setup page
    - `session/[id]/` - Live interview session page
    - `results/[id]/` - Interview results page
  - `auth/` - Authentication pages (login/signup)

## Backend Integration

The frontend communicates with the backend API running at `http://localhost:8000`. Make sure the backend server is running before using the application.

## Learn More

To learn more about the technologies used in this project:

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://reactjs.org/docs/getting-started.html)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Monaco Editor](https://github.com/suren-atoyan/monaco-react)
- [WebRTC](https://webrtc.org/getting-started/overview)
