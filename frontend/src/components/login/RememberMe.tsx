import React from 'react';
import { Link } from 'react-router-dom';

interface RememberMeProps extends React.InputHTMLAttributes<HTMLInputElement> {
  forgotPasswordPath?: string;
}

const RememberMe = React.forwardRef<HTMLInputElement, RememberMeProps>(
  ({ forgotPasswordPath = '/forgot-password', ...props }, ref) => {
    return (
      <div className="flex items-center justify-between text-xs pt-0.5 w-full select-none">
        <label className="flex items-center gap-2 cursor-pointer group">
          <input
            type="checkbox"
            ref={ref}
            className="w-4 h-4 rounded border-slate-800 bg-[#060a14] text-blue-600 focus:ring-offset-[#0a0f1d] focus:ring-1 focus:ring-[#00f2ff] cursor-pointer transition-all"
            {...props}
          />
          <span className="text-slate-400 group-hover:text-slate-200 transition-colors">
            Remember me
          </span>
        </label>
        <Link
          to={forgotPasswordPath}
          className="text-[#00f2ff] hover:text-cyan-300 font-semibold transition-colors cursor-pointer"
        >
          Forgot password?
        </Link>
      </div>
    );
  }
);

RememberMe.displayName = 'RememberMe';

export default RememberMe;
