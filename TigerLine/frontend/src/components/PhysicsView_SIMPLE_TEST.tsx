// SIMPLE TEST - Verify coordinate system works
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from 'recharts';

export default function PhysicsViewSimpleTest() {
  // Create simple test data: beach that slopes from bottom-left to top-right
  const testData = [
    { x: 500, y: -7 },  // Offshore: far left, deep (bottom)
    { x: 400, y: -6 },
    { x: 300, y: -5 },
    { x: 200, y: -3.5 },
    { x: 100, y: -2 },
    { x: 50, y: -1 },
    { x: 0, y: 0 }      // Shore: far right, shallow (top)
  ];

  return (
    <div style={{ background: 'white', padding: '40px' }}>
      <h2>SIMPLE TEST: Beach Cross-Section</h2>
      <p>Should slope from BOTTOM-LEFT (offshore, deep) to TOP-RIGHT (shore, shallow)</p>
      
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={testData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="x" 
            reversed={true}
            label={{ value: 'Distance from Shore (m) - Offshore LEFT, Shore RIGHT', position: 'bottom' }}
          />
          <YAxis 
            reversed={true}
            label={{ value: 'Depth (m) - Shallow TOP, Deep BOTTOM', angle: -90, position: 'insideLeft' }}
            domain={[-8, 1]}
          />
          <Line 
            type="monotone" 
            dataKey="y" 
            stroke="#000000" 
            strokeWidth={4}
            dot={{ r: 6, fill: '#FF0000' }}
          />
        </LineChart>
      </ResponsiveContainer>

      <div style={{ marginTop: '20px', fontSize: '14px' }}>
        <p><strong>Expected:</strong> Black line going from bottom-left to top-right</p>
        <p><strong>Data:</strong></p>
        <ul>
          <li>x=500m (offshore): y=-7 → Should plot at BOTTOM-LEFT</li>
          <li>x=0m (shore): y=0 → Should plot at TOP-RIGHT</li>
        </ul>
      </div>
    </div>
  );
}

