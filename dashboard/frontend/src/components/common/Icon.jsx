import {
  Shield, House, Layers3, ScanLine, PanelsTopLeft, ClipboardList,
  UserRound, ArrowLeftRight, ShieldPlus, FileText, Bell, ChevronDown,
  ChevronRight, Check, X, ChevronsRight, Clock3, Menu, FlaskConical,
  Eye, EyeOff, LogOut, CircleAlert, Users, UserPlus, Play,
} from 'lucide-react';

const icons = {
  shield: Shield, home: House, layers: Layers3, login: ScanLine,
  dashboard: PanelsTopLeft, onboarding: ClipboardList, profiles: UserRound,
  transactions: ArrowLeftRight, screening: ShieldPlus, reports: FileText,
  bell: Bell, chevronDown: ChevronDown, chevronRight: ChevronRight,
  check: Check, close: X, skip: ChevronsRight, clock: Clock3,
  menu: Menu, sample: FlaskConical, eye: Eye, eyeOff: EyeOff,
  logout: LogOut, alert: CircleAlert, users: Users, userPlus: UserPlus, play: Play,
};

export default function Icon({ name, size = 24, ...props }) {
  const Component = icons[name] || Layers3;
  return <Component size={size} strokeWidth={1.9} aria-hidden="true" {...props} />;
}
