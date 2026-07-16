import GoogleIcon from '../icons/GoogleIcon.tsx';
import AzureIcon from '../icons/AzureIcon.tsx';

interface FooterProps {
  onGoogleSignIn?: () => void;
  onAzureSignIn?: () => void;
}

export default function Footer({ onGoogleSignIn, onAzureSignIn }: FooterProps) {
  return (
    <div className="w-full space-y-6">
      {/* Divider */}
      <div className="relative text-center">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-slate-800" />
        </div>
        <span className="relative bg-[#0a0f1d] px-3 text-[10px] text-slate-500 uppercase font-semibold tracking-widest">
          or continue with sso
        </span>
      </div>

      {/* SSO Buttons */}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={onGoogleSignIn}
          className="flex items-center justify-center gap-2.5 bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800 hover:border-slate-700 text-slate-200 hover:text-white font-medium text-xs py-3 px-4 rounded-xl transition-all duration-200 cursor-pointer"
        >
          <GoogleIcon className="w-4 h-4" />
          <span>Google</span>
        </button>
        <button
          type="button"
          onClick={onAzureSignIn}
          className="flex items-center justify-center gap-2.5 bg-slate-900/40 hover:bg-slate-900/80 border border-slate-800 hover:border-slate-700 text-slate-200 hover:text-white font-medium text-xs py-3 px-4 rounded-xl transition-all duration-200 cursor-pointer"
        >
          <AzureIcon className="w-4 h-4" />
          <span>Azure AD</span>
        </button>
      </div>

      {/* Support details */}
      <div className="text-center pt-2">
        <p className="text-xs text-slate-500">
          Need an enterprise account?{' '}
          <a href="mailto:support@electricai.com" className="text-[#00f2ff] hover:underline font-medium">
            Contact Support
          </a>
        </p>
      </div>
    </div>
  );
}
