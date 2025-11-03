import { useState } from 'react';

type Props = {
  password: string;
  setPassword: (value: string) => void;
};

function PasswordInput({ password, setPassword }: Props) {
  const [show, setShow] = useState(false);

  return (
    <div className='mb-3'>
      <label className='form-label'>Heslo</label>

      <div className='input-group'>
        <input
          type={show ? 'text' : 'password'}
          className='form-control'
          value={password}
          onChange={e => setPassword(e.target.value)}
          placeholder='Zadejte heslo'
        />

        <button
          className='btn btn-primary text-white'
          onClick={() => setShow(!show)}
        >
          {show ? 'Skrýt' : 'Zobrazit'}
        </button>
      </div>
    </div>
  );
}

export default PasswordInput;
