import { Link } from 'react-router-dom';
import AppFooter from './AppFooter';
import Logo from '../Logo';

type AuthShellProps = {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footerLink?: { label: string; to: string; prompt: string };
};

export default function AuthShell({ title, subtitle, children, footerLink }: AuthShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-navy">
      <div className="flex flex-1 flex-col md:flex-row">
        <section className="relative hidden flex-1 items-center justify-center overflow-hidden bg-gradient-to-br from-navy via-background to-surface-container p-12 md:flex">
          <div className="absolute -right-16 -top-16 h-48 w-48 rounded-full bg-secondary/20 blur-3xl" />
          <div className="absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-primary-container/20 blur-3xl" />
          <div className="relative z-10 max-w-md text-center">
            <div className="mx-auto mb-8 flex h-48 w-48 items-center justify-center rounded-full border-2 border-dashed border-primary/30 bg-primary-container/5">
              <Logo variant="mark" size={112} />
            </div>
            <h1 className="font-display text-headline-lg text-on-surface">
              Osiągnij <span className="text-primary">mistrzostwo</span> dzięki AI
            </h1>
            <p className="mt-4 text-on-surface-variant">
              Twoje treningi, Twoje postępy, Twoja przewaga. Analiza techniki odbicia dolnego w czasie rzeczywistym.
            </p>
          </div>
        </section>

        <section className="flex flex-1 items-center justify-center bg-surface p-6 md:p-12">
          <div className="w-full max-w-md space-y-8">
            <div className="flex flex-col items-center md:items-start">
              <div className="mb-4 flex items-center gap-3">
                <Logo size={48} />
                <div>
                  <p className="font-display text-xl font-bold text-primary">Cyber-Trener</p>
                  <p className="text-xs uppercase tracking-widest text-on-surface-variant">Siatkarz</p>
                </div>
              </div>
              <h2 className="font-display text-headline-lg text-on-surface">{title}</h2>
              <p className="mt-1 text-on-surface-variant">{subtitle}</p>
            </div>
            {children}
            {footerLink && (
              <p className="text-center text-sm text-on-surface-variant md:text-left">
                {footerLink.prompt}{' '}
                <Link to={footerLink.to} className="font-semibold text-primary hover:underline">
                  {footerLink.label}
                </Link>
              </p>
            )}
          </div>
        </section>
      </div>
      <AppFooter />
    </div>
  );
}
