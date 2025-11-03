import { useEffect, useState } from 'react';

type Props = {
  password: string;
};
type PasswordResult = {
  label: 'Slabé' | 'Střední' | 'Silné';
  score: number;
};

function PasswordStrength({ password }: Props) {
  const [passwordStrength, setPasswordStrength] = useState<
    'Slabé' | 'Střední' | 'Silné'
  >('Slabé');
  const [score, setScore] = useState(0);

  const evaluatePassword = (password: string): PasswordResult => {
    const hasLength = password.length >= 8;
    const hasUpper = /[A-Z]/.test(password);
    const hasNumber = /\d/.test(password);
    const hasSpecial = /[!@#$%^&*]/.test(password);

    const score =
      Number(hasLength) +
      Number(hasUpper) +
      Number(hasNumber) +
      Number(hasSpecial);

    if (score === 4) return { label: 'Silné', score };
    if (score >= 2) return { label: 'Střední', score };
    return { label: 'Slabé', score };
  };

  useEffect(() => {
    const result = evaluatePassword(password);
    //eslint-disable-next-line react-hooks/set-state-in-effect
    setPasswordStrength(result.label);
    setScore(result.score);
  }, [password]);

  useEffect(() => {
    document.title = `Síla hesla: ${passwordStrength}`;
  }, [passwordStrength]);
  let color = 'bg-danger';

  if (passwordStrength === 'Střední') color = 'bg-warning';
  if (passwordStrength === 'Silné') color = 'bg-success';

  const width = (score / 4) * 100;

  return (
    <div>
      <div className='progress mb-2'>
        <div
          className={`progress-bar ${color}`}
          style={{ width: `${width}%` }}
        />
      </div>

      <p>
        Síla hesla: <strong>{passwordStrength}</strong>
      </p>
    </div>
  );
}

export default PasswordStrength;
