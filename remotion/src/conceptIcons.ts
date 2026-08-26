/** Keyword -> icon mapping so the visual actually tracks what's being said
 * (e.g. narration mentions "mot de passe" -> show a key icon), instead of a
 * generic shape. Curated for this training's real vocabulary (cybersecurity
 * awareness), matched against lowercase, accent-stripped caption text.
 * Icon names must be valid lucide-react exports (verified against the
 * installed package - see verify-icons.mjs). Ordered roughly
 * specific-to-generic; the first matching entry wins. */
export const CONCEPT_ICONS: Array<{ keywords: string[]; icon: string }> = [
  // People / actors
  { keywords: ["hacker", "cybercriminel", "pirate", "attaquant"], icon: "UserX" },
  { keywords: ["employe", "collegue", "collaborateur", "personne", "utilisateur"], icon: "User" },
  { keywords: ["equipe", "collegues"], icon: "Users" },
  { keywords: ["client", "clients"], icon: "Handshake" },
  { keywords: ["victime"], icon: "UserMinus" },

  // Threats
  { keywords: ["hamecon", "phishing"], icon: "Fish" },
  { keywords: ["ransomware", "rancon", "rancongiciel"], icon: "Siren" },
  { keywords: ["virus", "malware", "logiciel malveillant"], icon: "Bug" },
  { keywords: ["attaque", "menace"], icon: "Swords" },
  { keywords: ["vulnerabilite", "faille"], icon: "ShieldAlert" },
  { keywords: ["incident"], icon: "TriangleAlert" },
  { keywords: ["danger", "risque"], icon: "AlertOctagon" },
  { keywords: ["fuite"], icon: "Unlock" },

  // Protections / mechanisms
  { keywords: ["mot de passe", "identifiant", "identifiants"], icon: "KeyRound" },
  { keywords: ["cle", "cles"], icon: "Key" },
  { keywords: ["chiffrement", "crypte", "cryptage"], icon: "Lock" },
  { keywords: ["confidentialite"], icon: "EyeOff" },
  { keywords: ["integrite"], icon: "ShieldCheck" },
  { keywords: ["disponibilite"], icon: "Zap" },
  { keywords: ["authentification", "mfa", "double facteur", "biometrie"], icon: "Fingerprint" },
  { keywords: ["pare-feu", "firewall"], icon: "Flame" },
  { keywords: ["edr", "detection"], icon: "Radar" },
  { keywords: ["antivirus"], icon: "ShieldPlus" },
  { keywords: ["securite", "protection", "bouclier"], icon: "Shield" },
  { keywords: ["mise a jour", "patch", "correctif"], icon: "RefreshCw" },
  { keywords: ["sauvegarde", "backup"], icon: "HardDriveDownload" },
  { keywords: ["controle d'acces", "acces"], icon: "DoorOpen" },
  { keywords: ["audit", "conformite"], icon: "ClipboardCheck" },
  { keywords: ["reglementation", "loi", "rgpd", "dgssi", "cndp"], icon: "Scale" },

  // Tech / infra
  { keywords: ["intelligence artificielle", "chatgpt", "gpt", "ia generative", "ia "], icon: "Sparkles" },
  { keywords: ["code", "developpeur", "developpement"], icon: "Code2" },
  { keywords: ["cloud", "nuage"], icon: "Cloud" },
  { keywords: ["donnees", "base de donnees"], icon: "Database" },
  { keywords: ["serveur"], icon: "Server" },
  { keywords: ["ordinateur", "poste de travail", "pc"], icon: "Laptop" },
  { keywords: ["smartphone", "telephone", "mobile"], icon: "Smartphone" },
  { keywords: ["wifi", "reseau"], icon: "Wifi" },
  { keywords: ["email", "mail", "courriel"], icon: "Mail" },
  { keywords: ["reunion", "teams", "visioconference"], icon: "Video" },
  { keywords: ["internet", "navigateur", "site web", "lien"], icon: "Globe" },
  { keywords: ["carte bancaire", "carte de credit"], icon: "CreditCard" },

  // Business / outcomes
  { keywords: ["entreprise", "societe", "organisation"], icon: "Building2" },
  { keywords: ["banque", "bancaire"], icon: "Landmark" },
  { keywords: ["argent", "cout", "financier", "perte"], icon: "Banknote" },
  { keywords: ["formation", "sensibilisation", "apprendre"], icon: "GraduationCap" },
  { keywords: ["contrat", "signature"], icon: "FileSignature" },
  { keywords: ["temps", "delai", "heure"], icon: "Clock" },

  // Generic reactions
  { keywords: ["question"], icon: "HelpCircle" },
  { keywords: ["important", "attention", "vigilance"], icon: "AlertCircle" },
  { keywords: ["interdit", "ne pas", "jamais"], icon: "Ban" },
  { keywords: ["valide", "correct", "bonne pratique"], icon: "CheckCircle2" },
  { keywords: ["cible"], icon: "Target" },
  { keywords: ["surveillance", "observer"], icon: "Eye" },
];

const DEFAULT_ICON = "ShieldCheck";

function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

export function matchConceptIcon(text: string): string {
  const normalized = stripAccents(text.toLowerCase());
  for (const entry of CONCEPT_ICONS) {
    for (const kw of entry.keywords) {
      if (normalized.includes(stripAccents(kw))) {
        return entry.icon;
      }
    }
  }
  return DEFAULT_ICON;
}

/** True if a short word/group is one of our curated concept keywords (or a
 * generic emphasis word) - used to highlight it in the captions, Opus/
 * InVideo style, rather than rendering every word the same weight. */
const EXTRA_EMPHASIS = [
  "jamais", "toujours", "important", "attention", "obligatoire", "interdit",
  "gratuit", "urgent", "confidentiel", "securise", "vulnerable",
];

export function isEmphasisWord(text: string): boolean {
  const normalized = stripAccents(text.toLowerCase()).replace(/[.,!?;:]/g, "");
  if (!normalized) return false;
  for (const w of EXTRA_EMPHASIS) {
    if (normalized.includes(stripAccents(w))) return true;
  }
  for (const entry of CONCEPT_ICONS) {
    for (const kw of entry.keywords) {
      if (normalized.includes(stripAccents(kw)) || stripAccents(kw).includes(normalized)) {
        return true;
      }
    }
  }
  return false;
}
